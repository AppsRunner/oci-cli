"""
Legal document views with explicit HTTP cache headers.

Cache strategy:
  - Public legal documents  → Cache-Control: public, max-age=300, stale-while-revalidate=60
  - Document lists/search   → Cache-Control: public, max-age=60
  - Authenticated endpoints → Cache-Control: private, no-store
"""
import hashlib

from django.http import JsonResponse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.views import View
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.vary import vary_on_headers
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LegalDocument
from .serializers import LegalDocumentDetailSerializer, LegalDocumentListSerializer

_LEGAL_DOC_CACHE_TTL = 300   # 5 minutes — aligned with OCI WAA / Nginx proxy_cache_valid
_LIST_CACHE_TTL = 60         # 1 minute — list pages change more often


def _set_public_cache(response, max_age: int, stale_while_revalidate: int = 60) -> None:
    """Stamp public Cache-Control and Vary headers on a DRF/Django response."""
    patch_cache_control(
        response,
        public=True,
        max_age=max_age,
        s_maxage=max_age,
        stale_while_revalidate=stale_while_revalidate,
    )
    patch_vary_headers(response, ("Accept", "Accept-Language"))


def _set_private_cache(response) -> None:
    patch_cache_control(response, private=True, no_store=True)


class LegalDocumentDetailView(APIView):
    """
    GET /api/legal/<slug>/

    Public legal documents are served with a 5-minute public cache.
    Draft / restricted documents fall back to private, no-store.
    """
    permission_classes = [AllowAny]

    def get(self, request, slug: str):
        try:
            doc = LegalDocument.objects.select_related("category", "author").get(
                slug=slug, is_published=True
            )
        except LegalDocument.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = LegalDocumentDetailSerializer(doc, context={"request": request})
        response = Response(serializer.data)

        if doc.is_public:
            _set_public_cache(response, max_age=_LEGAL_DOC_CACHE_TTL)
            # ETag based on last-modified timestamp so CDN can do conditional GETs
            etag = hashlib.md5(
                f"{doc.slug}:{doc.updated_at.isoformat()}".encode()
            ).hexdigest()
            response["ETag"] = f'"{etag}"'
            response["Last-Modified"] = doc.updated_at.strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            )
        else:
            # Subscriber-only or restricted document
            _set_private_cache(response)

        return response


class LegalDocumentListView(APIView):
    """
    GET /api/legal/
    GET /api/legal/?category=<slug>&page=<n>

    Publicly cacheable list of published documents.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        qs = (
            LegalDocument.objects
            .filter(is_published=True, is_public=True)
            .select_related("category")
            .order_by("-published_at")
        )

        category = request.query_params.get("category")
        if category:
            qs = qs.filter(category__slug=category)

        serializer = LegalDocumentListSerializer(qs[:50], many=True, context={"request": request})
        response = Response({"results": serializer.data, "count": qs.count()})

        _set_public_cache(response, max_age=_LIST_CACHE_TTL, stale_while_revalidate=30)
        # Vary on Accept-Language so Bengali and English lists are cached separately
        patch_vary_headers(response, ("Accept-Language",))

        return response


@api_view(["GET"])
@permission_classes([AllowAny])
@cache_page(_LEGAL_DOC_CACHE_TTL, cache="default", key_prefix="legal_pdf")
def legal_document_pdf(request, slug: str):
    """
    GET /api/legal/<slug>/pdf/

    Returns the PDF download URL.  Cached in Redis via @cache_page.
    """
    try:
        doc = LegalDocument.objects.get(slug=slug, is_published=True, is_public=True)
    except LegalDocument.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    return Response({"pdf_url": request.build_absolute_uri(doc.pdf_file.url)})


class UserBookmarkView(APIView):
    """
    POST /api/legal/<slug>/bookmark/

    Authenticated — must never be cached.
    """
    permission_classes = [IsAuthenticated]

    @never_cache
    def post(self, request, slug: str):
        try:
            doc = LegalDocument.objects.get(slug=slug, is_published=True)
        except LegalDocument.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        request.user.bookmarks.add(doc)
        response = Response({"bookmarked": True}, status=status.HTTP_201_CREATED)
        _set_private_cache(response)
        return response
