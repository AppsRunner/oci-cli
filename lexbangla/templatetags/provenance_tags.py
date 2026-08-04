"""
Template tag: {% provenance_block block %}

Renders a single ProvenanceBlock with the ProvenanceTooltip component.
Colour coding:
  binding_law      → green border
  doctrinal_context → blue border
  verify_case      → yellow border (unverified)
  narrative        → no border
  cross_reference  → grey border
"""

import json
from django import template
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string

register = template.Library()

_BLOCK_COLORS = {
    "binding_law": "border-green-600",
    "doctrinal_context": "border-blue-500",
    "verify_case": "border-yellow-400",
    "narrative": "border-transparent",
    "cross_reference": "border-gray-400",
}


@register.simple_tag
def provenance_block(block):
    """Render a ProvenanceBlock with hover tooltip."""
    ctx = {
        "block": block,
        "tooltip_data": mark_safe(json.dumps(block.to_tooltip_dict())),
        "border_class": _BLOCK_COLORS.get(block.block_type, "border-transparent"),
        "is_verify": block.block_type == "verify_case",
    }
    return render_to_string("lexbangla/components/provenance_block.html", ctx)


@register.inclusion_tag("lexbangla/components/provenance_tooltip_styles.html")
def provenance_tooltip_styles():
    """Include the ProvenanceTooltip CSS (call once per page in <head>)."""
    return {}
