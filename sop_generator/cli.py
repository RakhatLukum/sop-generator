import os
import argparse
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
    orchestrate_workflow,
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


def run_iterative(title: str, number: str, equipment: str, docs: List[str], sections: List[Dict[str, Any]]) -> Dict[str, Any]:
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
        max_iters=2,  # fast default
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

    return {"approved": loop_result.get("approved", False), "preview": preview, "logs": loop_result.get("logs", [])}


def run_groupchat_sequential(title: str, number: str, equipment: str, docs: List[str], sections: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Fallback transcript using a single round of sequential agent calls (no streaming)."""
    coord = build_coordinator(on_log=lambda m: None)
    sop_gen = build_sop_generator()
    safety = build_safety_agent()
    critic = build_critic()
    quality = build_quality_checker()
    styler = build_content_styler()

    chunks = parse_documents_to_chunks(docs)
    corpus_summary = summarize_parsed_chunks(chunks)

    instructions = build_generation_instruction(
        sop_title=title,
        sop_number=number,
        equipment_type=equipment,
        sections=sections,
        parsed_corpus_summary=corpus_summary if corpus_summary else None,
        critique_feedback=None,
    )

    transcript: List[Dict[str, str]] = []

    def _collect(agent_name: str, messages) -> None:
        contents = [getattr(m, "content", str(m)) for m in messages]
        if contents:
            transcript.append({"sender": agent_name, "content": "\n\n".join(contents)})

    # Generator
    from agents.coordinator import _run_agent_and_get_messages  # reuse helper
    gen_msgs = _run_agent_and_get_messages(sop_gen, instructions)
    _collect("SOP_Generator", gen_msgs)

    # Safety
    safety_msgs = _run_agent_and_get_messages(safety, f"Проверь раздел безопасности и добавь недостающее.\nТЕКСТ:\n{transcript[-1]['content']}")
    _collect("Safety_Agent", safety_msgs)

    # Quality
    quality_msgs = _run_agent_and_get_messages(quality, f"Проверь качество. Верни только список проблем и предложения.\nТЕКСТ:\n{transcript[-1]['content']}")
    _collect("Quality_Checker", quality_msgs)

    # Critic
    critic_msgs = _run_agent_and_get_messages(critic, f"Оцени документ по протоколу (SUMMARY/ISSUES/STATUS).\nТЕКСТ:\n{transcript[-1]['content']}")
    _collect("Critic", critic_msgs)

    # Styler
    styled_msgs = _run_agent_and_get_messages(styler, f"Приведи текст к корпоративному стилю.\nТЕКСТ:\n{transcript[-1]['content']}")
    _collect("Content_Styler", styled_msgs)

    return transcript


def run_groupchat(title: str, number: str, equipment: str, docs: List[str], sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Try real GroupChat first; on server limitations (streaming/connection), fall back to sequential transcript
    try:
        coord = build_coordinator(on_log=lambda m: None)
        sop_gen = build_sop_generator()
        safety = build_safety_agent()
        critic = build_critic()
        quality = build_quality_checker()
        styler = build_content_styler()

        chunks = parse_documents_to_chunks(docs)
        corpus_summary = summarize_parsed_chunks(chunks)

        instructions = build_generation_instruction(
            sop_title=title,
            sop_number=number,
            equipment_type=equipment,
            sections=sections,
            parsed_corpus_summary=corpus_summary if corpus_summary else None,
            critique_feedback=None,
        )

        messages = orchestrate_workflow(
            coordinator=coord,
            agents=[sop_gen, safety, critic, quality, styler],
            instructions=instructions,
            max_rounds=8,
        )
        return {"messages": messages}
    except Exception:
        # Fallback transcript without streaming
        transcript = run_groupchat_sequential(title, number, equipment, docs, sections)
        return {"messages": transcript}


def main() -> None:
    ap = argparse.ArgumentParser(description="Run SOP generation agents (CLI)")
    ap.add_argument("--title", required=True)
    ap.add_argument("--number", required=True)
    ap.add_argument("--equipment", default="")
    ap.add_argument("--doc", action="append", default=[], help="Path to reference document. Repeatable.")
    ap.add_argument("--section", action="append", default=[], help="Section spec: 'Title|ai|optional prompt'. Repeatable.")
    ap.add_argument("--out", default=os.path.join("docs", "sop_generated.md"))
    ap.add_argument("--mode", choices=["iterative", "groupchat"], default="iterative")
    ap.add_argument("--transcript", default=os.path.join("docs", "sop_transcript.md"), help="Where to save groupchat/iterative transcript")
    ap.add_argument("--save-transcript", action="store_true", help="Also save transcript for iterative mode")
    args = ap.parse_args()

    sections = [_parse_section_arg(s) for s in args.section]

    if args.mode == "groupchat":
        result = run_groupchat(args.title, args.number, args.equipment, args.doc, sections)
        os.makedirs(os.path.dirname(args.transcript), exist_ok=True)
        with open(args.transcript, "w", encoding="utf-8") as tf:
            tf.write(f"# GroupChat transcript for {args.title} ({args.number})\n\n")
            for m in result.get("messages", []):
                tf.write(f"### {m.get('sender','unknown')}\n\n{m.get('content','')}\n\n")
        print(os.path.abspath(args.transcript))
        return

    # iterative (default)
    result = run_iterative(args.title, args.number, args.equipment, args.doc, sections)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as mf:
        mf.write(f"# {args.title}\n\n")
        if args.number:
            mf.write(f"Номер: {args.number}\n\n")
        for idx, sec in enumerate(result["preview"], start=1):
            mf.write(f"## {idx}. {sec['title']}\n\n{sec.get('content','')}\n\n")

    if args.save_transcript:
        os.makedirs(os.path.dirname(args.transcript), exist_ok=True)
        with open(args.transcript, "w", encoding="utf-8") as tf:
            tf.write(f"# Iterative transcript for {args.title} ({args.number})\n\n")
            for entry in result.get("logs", []):
                tf.write(f"- {entry}\n")
        
    print(os.path.abspath(args.out))


if __name__ == "__main__":
    main() 