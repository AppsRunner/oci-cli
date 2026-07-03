/**
 * /legal/[slug] — Legal document page with Incremental Static Regeneration.
 *
 * ISR strategy:
 *  - Build time: pre-render the 50 most-viewed documents (getStaticPaths).
 *  - On-demand:  unknown slugs are server-rendered on first request, then
 *                cached as static pages (fallback: 'blocking').
 *  - Freshness:  every page revalidates after REVALIDATE_SECONDS so edits
 *                propagate without a full rebuild.
 */

import Head from 'next/head';
import { notFound } from 'next/navigation';

/** Edge / CDN cache TTL must match next.config.js headers s-maxage */
const REVALIDATE_SECONDS = 300; // 5 minutes

// ------------------------------------------------------------------ //
// Data fetching
// ------------------------------------------------------------------ //

async function fetchLegalDocument(slug) {
  const res = await fetch(
    `${process.env.DJANGO_API_URL}/api/legal/${encodeURIComponent(slug)}/`,
    { next: { revalidate: REVALIDATE_SECONDS } }
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API error ${res.status} for /api/legal/${slug}/`);
  return res.json();
}

async function fetchTopDocumentSlugs() {
  const res = await fetch(
    `${process.env.DJANGO_API_URL}/api/legal/?ordering=-view_count&page_size=50`,
    { cache: 'no-store' } // Always fetch fresh slugs at build time
  );
  if (!res.ok) return [];
  const data = await res.json();
  return (data.results ?? []).map((doc) => doc.slug);
}

// ------------------------------------------------------------------ //
// ISR — getStaticPaths
// ------------------------------------------------------------------ //

export async function getStaticPaths() {
  let slugs = [];
  try {
    slugs = await fetchTopDocumentSlugs();
  } catch {
    // Network error at build time → start with no pre-rendered pages;
    // they will be built on-demand via fallback: 'blocking'.
  }

  return {
    paths: slugs.map((slug) => ({ params: { slug } })),
    // 'blocking': unknown slugs are SSR on first request, then cached.
    // This gives search-engine bots a fully-rendered page on first visit.
    fallback: 'blocking',
  };
}

// ------------------------------------------------------------------ //
// ISR — getStaticProps
// ------------------------------------------------------------------ //

export async function getStaticProps({ params }) {
  const { slug } = params;

  let doc;
  try {
    doc = await fetchLegalDocument(slug);
  } catch (err) {
    console.error(`[ISR] Failed to fetch /api/legal/${slug}/`, err);
    // Return 500-like behaviour: let Next.js serve a stale page if available
    return { revalidate: 60 }; // Retry quickly
  }

  if (!doc) {
    return { notFound: true, revalidate: REVALIDATE_SECONDS };
  }

  return {
    props: { doc },
    revalidate: REVALIDATE_SECONDS,
  };
}

// ------------------------------------------------------------------ //
// Page component
// ------------------------------------------------------------------ //

export default function LegalDocumentPage({ doc }) {
  if (!doc) {
    notFound();
  }

  const {
    title,
    title_en,
    slug,
    category,
    body_html,
    summary,
    published_at,
    updated_at,
    pdf_url,
  } = doc;

  const formattedDate = new Intl.DateTimeFormat('bn-BD', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(new Date(published_at));

  const canonicalUrl = `https://lexbangla.com/legal/${slug}`;

  return (
    <>
      <Head>
        <title>{`${title} — LexBangla`}</title>
        <meta name="description" content={summary} />
        <link rel="canonical" href={canonicalUrl} />

        {/* Open Graph */}
        <meta property="og:type"        content="article" />
        <meta property="og:title"       content={title} />
        <meta property="og:description" content={summary} />
        <meta property="og:url"         content={canonicalUrl} />
        <meta property="og:locale"      content="bn_BD" />
        <meta property="og:locale:alternate" content="en_US" />

        {/* Article structured data */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'LegalDocument',
              name: title,
              alternativeName: title_en,
              url: canonicalUrl,
              datePublished: published_at,
              dateModified: updated_at,
              inLanguage: 'bn',
            }),
          }}
        />
      </Head>

      <article className="legal-document">
        <header className="legal-document__header">
          {category && (
            <span className="legal-document__category">{category.name}</span>
          )}
          <h1 className="legal-document__title">{title}</h1>
          {title_en && (
            <p className="legal-document__title-en">{title_en}</p>
          )}
          <time
            className="legal-document__date"
            dateTime={published_at}
          >
            {formattedDate}
          </time>
          {pdf_url && (
            <a
              href={pdf_url}
              className="legal-document__pdf-link"
              download
              rel="noopener noreferrer"
            >
              PDF ডাউনলোড করুন
            </a>
          )}
        </header>

        {summary && (
          <section className="legal-document__summary" aria-label="সারসংক্ষেপ">
            <p>{summary}</p>
          </section>
        )}

        <section
          className="legal-document__body"
          dangerouslySetInnerHTML={{ __html: body_html }}
        />
      </article>
    </>
  );
}
