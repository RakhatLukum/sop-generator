import os
import argparse
from typing import List, Dict, Any

from sop_generator.config.agent_config import (
    build_sop_generator,
    build_critic,
    build_generation_instruction,
    summarize_parsed_chunks,
    iterative_generate_until_approved,
)
from sop_generator.utils.document_processor import parse_documents_to_chunks


def _parse_section_arg(raw: str) -> Dict[str, Any]:
    # Format: Title|mode|prompt(optional)
    parts = raw.split("|", 2)
    title = parts[0].strip()
    mode = (parts[1].strip() if len(parts) > 1 else "ai")
    prompt = (parts[2].strip() if len(parts) > 2 else "")
    return {"title": title, "mode": mode, "prompt": prompt, "content": ""}


def run_iterative(title: str, number: str, equipment: str, docs: List[str], sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    sop_gen = build_sop_generator()
    critic = build_critic()

    chunks = parse_documents_to_chunks(docs)
    corpus_summary = summarize_parsed_chunks(chunks)

    if not sections:
        raise ValueError("Необходимо указать хотя бы один раздел (--section)")

    def base_instruction_builder(critique: str) -> str:
        return build_generation_instruction(
            sop_title=title,
            sop_number=number,
            equipment_type=equipment,
            sections=sections,
            parsed_corpus_summary=corpus_summary if corpus_summary else None,
            critique_feedback=critique or None,
        )

    def _cli_logger(message: str) -> None:
        print(f"[SOP] {message}", flush=True)

    loop_result = iterative_generate_until_approved(
        sop_gen=sop_gen,
        critic=critic,
        base_instruction_builder=base_instruction_builder,
        sections=sections,
        max_iters=5,
        enforce_mandatory_sections=False,
        logger=_cli_logger,
        auto_backfill_meta={
            "title": title,
            "number": number,
            "equipment": equipment,
            "equipment_type": equipment,
        },
        auto_backfill_summary=corpus_summary if corpus_summary else None,
    )

    generated_full_text = loop_result.get("content", "")

    return {
        "approved": loop_result.get("approved", False),
        "content": generated_full_text,
        "logs": loop_result.get("logs", []),
    }


# Group chat modes removed to simplify to two-agent workflow


def main() -> None:
    ap = argparse.ArgumentParser(description="Run SOP generation (Generator + Critic)")
    ap.add_argument("--title", required=True)
    ap.add_argument("--number", required=True)
    ap.add_argument("--equipment", default="")
    ap.add_argument("--doc", action="append", default=[], help="Path to reference document. Repeatable.")
    ap.add_argument("--section", action="append", default=[], help="Section spec: 'Title|ai|optional prompt'. Repeatable.")
    ap.add_argument("--out", default=os.path.join("docs", "sop_generated.md"))
    ap.add_argument("--transcript", default=os.path.join("docs", "sop_transcript.md"), help="Where to save iterative transcript")
    ap.add_argument("--save-transcript", action="store_true", help="Also save transcript for iterative mode")
    args = ap.parse_args()

    sections = [_parse_section_arg(s) for s in args.section]

    # iterative only
    result = run_iterative(args.title, args.number, args.equipment, args.doc, sections)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as mf:
        mf.write(f"# {args.title}\n\n")
        if args.number:
            mf.write(f"Номер: {args.number}\n\n")
        content = (result.get("content") or "").strip()
        if content:
            mf.write(content + "\n")

    if args.save_transcript:
        os.makedirs(os.path.dirname(args.transcript), exist_ok=True)
        with open(args.transcript, "w", encoding="utf-8") as tf:
            tf.write(f"# Iterative transcript for {args.title} ({args.number})\n\n")
            for entry in result.get("logs", []):
                tf.write(f"- {entry}\n")
        
    print(os.path.abspath(args.out))


if __name__ == "__main__":
    main() 
