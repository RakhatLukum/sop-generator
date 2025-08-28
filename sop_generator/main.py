import os
import argparse
import tempfile
from typing import List, Dict, Any

from agents import (
    build_coordinator,
    build_sop_generator,
    build_document_parser,
    build_content_styler,
    build_critic,
    build_quality_checker,
    build_safety_agent,
    build_generation_instruction,
    summarize_parsed_chunks,
)
from agents.coordinator import iterative_generate_until_approved
from utils.document_processor import parse_documents_to_chunks


def _parse_section_arg(raw: str) -> Dict[str, Any]:
    # Format: Title|mode|prompt(optional)
    parts = raw.split("|", 2)
    title = parts[0].strip()
    mode = (parts[1].strip() if len(parts) > 1 else "ai")
    prompt = (parts[2].strip() if len(parts) > 2 else "")
    return {"title": title, "mode": mode, "prompt": prompt, "content": ""}


def run_agents(title: str, number: str, equipment: str, docs: List[str], sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    coord = build_coordinator(on_log=lambda m: None)
    sop_gen = build_sop_generator()
    doc_parser = build_document_parser()
    styler = build_content_styler()
    critic = build_critic()
    quality = build_quality_checker()
    safety = build_safety_agent()

    chunks = parse_documents_to_chunks(docs)
    corpus_summary = summarize_parsed_chunks(chunks)

    def base_instruction_builder(critique: str) -> str:
        return build_generation_instruction(
            sop_title=title,
            sop_number=number,
            equipment_type=equipment,
            sections=sections,
            parsed_corpus_summary=corpus_summary if corpus_summary else None,
            critique_feedback=critique or None,
        )

    loop_result = iterative_generate_until_approved(
        coordinator=coord,
        sop_gen=sop_gen,
        safety=safety,
        critic=critic,
        quality=quality,
        styler=styler,
        base_instruction_builder=base_instruction_builder,
        max_iters=5,
        logger=lambda m: None,
    )

    generated_full_text = loop_result.get("content", "")

    preview = []
    parts = generated_full_text.split("\n\n")
    for idx, section in enumerate(sections):
        if section["mode"] == "manual":
            final_text = section.get("content", "")
        else:
            slice_text = "\n".join(parts[idx*3:(idx+1)*3]).strip()
            if section["mode"] == "ai+doc":
                top_chunks = chunks[:3]
                cites = "\n".join([f"Источник: {c['source']} | {c['keywords']}" for c in top_chunks])
                final_text = (section.get("content") or f"{slice_text}\n\n{cites}").strip()
            else:
                final_text = section.get("content") or slice_text or f"[AI placeholder] {section['title']}"
        preview.append({"title": section["title"], "content": final_text})

    return {"approved": loop_result.get("approved", False), "preview": preview}


def main() -> None:
    ap = argparse.ArgumentParser(description="Run SOP generation agents (no UI)")
    ap.add_argument("--title", required=True)
    ap.add_argument("--number", required=True)
    ap.add_argument("--equipment", default="")
    ap.add_argument("--doc", action="append", default=[], help="Path to reference document. Repeatable.")
    ap.add_argument("--section", action="append", default=[], help="Section spec: 'Title|ai|optional prompt'. Repeatable.")
    ap.add_argument("--out", default=os.path.join("docs", "sop_generated.md"))
    args = ap.parse_args()

    sections = [_parse_section_arg(s) for s in args.section]
    result = run_agents(args.title, args.number, args.equipment, args.doc, sections)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as mf:
        mf.write(f"# {args.title}\n\n")
        if args.number:
            mf.write(f"Номер: {args.number}\n\n")
        for idx, sec in enumerate(result["preview"], start=1):
            mf.write(f"## {idx}. {sec['title']}\n\n{sec.get('content','')}\n\n")
    print(os.path.abspath(args.out))


if __name__ == "__main__":
    main() 