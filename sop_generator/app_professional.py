import os
import json
import tempfile
from typing import List, Dict, Any, Optional
from datetime import datetime

import streamlit as st
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx

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
from utils.template_manager import load_template, apply_styles
from utils.export_manager import populate_docx, export_to_docx, export_to_pdf

# Professional grade systems
from utils.quality_assessment import ProfessionalSOPAssessor
from utils.equipment_engine import ProfessionalEquipmentEngine
from utils.safety_integration import ProfessionalSafetyIntegrator
from utils.content_validator import RealTimeContentValidator, ValidationLevel
from utils.improvement_engine import IterativeImprovementEngine, create_document_hash
from ui.dashboard_components import SOPReadinessDashboard, SOPMetricsDashboard, render_comparison_dashboard

APP_TITLE = "Professional SOP Generator - Production Grade System"


def init_professional_session_state() -> None:
    """Initialize session state for professional SOP generator"""
    
    # Basic metadata
    if "meta" not in st.session_state:
        st.session_state.meta = {
            "title": "",
            "number": "",
            "equipment": "",
            "equipment_type": "",
            "department": "",
            "author": "",
            "reviewer": "",
            "approver": ""
        }
    
    # File handling
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []
    if "reference_documents" not in st.session_state:
        st.session_state.reference_documents = []
    
    # Section configuration
    if "sections" not in st.session_state:
        st.session_state.sections = []
    if "mandatory_sections_added" not in st.session_state:
        st.session_state.mandatory_sections_added = False
    
    # Generation and validation
    if "logs" not in st.session_state:
        st.session_state.logs = []
    if "parsed_chunks" not in st.session_state:
        st.session_state.parsed_chunks = []
    if "preview" not in st.session_state:
        st.session_state.preview = []
    if "running" not in st.session_state:
        st.session_state.running = False
    if "worker" not in st.session_state:
        st.session_state.worker = None
    
    # Professional assessment results
    if "quality_assessment" not in st.session_state:
        st.session_state.quality_assessment = None
    if "validation_result" not in st.session_state:
        st.session_state.validation_result = None
    if "safety_analysis" not in st.session_state:
        st.session_state.safety_analysis = None
    if "equipment_analysis" not in st.session_state:
        st.session_state.equipment_analysis = None
    
    # Generation history for metrics
    if "generation_history" not in st.session_state:
        st.session_state.generation_history = []
    if "current_version" not in st.session_state:
        st.session_state.current_version = 1
    if "sop_versions" not in st.session_state:
        st.session_state.sop_versions = []
    
    # Improvement engine
    if "improvement_engine" not in st.session_state:
        st.session_state.improvement_engine = IterativeImprovementEngine()
    if "current_document_id" not in st.session_state:
        st.session_state.current_document_id = None
    if "user_feedback_given" not in st.session_state:
        st.session_state.user_feedback_given = False


def add_log(message: str) -> None:
    """Add log message with timestamp"""
    try:
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        if "logs" not in st.session_state:
            st.session_state.logs = []
        st.session_state.logs.append(formatted_message)
        st.session_state.logs = st.session_state.logs[-500:]  # Keep last 500 logs
    except Exception:
        pass


def ui_professional_home():
    """Enhanced home page with professional metadata collection"""
    
    st.markdown("# 🎯 Professional SOP Generator")
    st.markdown("### Production-Grade Standard Operating Procedure Generation System")
    
    with st.expander("📋 Document Metadata", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.session_state.meta["title"] = st.text_input(
                "SOP Title *", 
                value=st.session_state.meta.get("title", ""),
                help="Full descriptive title of the procedure"
            )
            st.session_state.meta["number"] = st.text_input(
                "SOP Number *", 
                value=st.session_state.meta.get("number", ""),
                help="Unique document identifier (e.g., SOP-001-2024)"
            )
            st.session_state.meta["equipment"] = st.text_input(
                "Equipment/System *", 
                value=st.session_state.meta.get("equipment", ""),
                help="Specific equipment model or system name"
            )
            st.session_state.meta["department"] = st.text_input(
                "Department", 
                value=st.session_state.meta.get("department", ""),
                help="Operating department or laboratory"
            )
        
        with col2:
            st.session_state.meta["equipment_type"] = st.selectbox(
                "Equipment Category",
                ["", "Chromatography", "Spectroscopy", "Microscopy", "Analytical Balance", 
                 "Centrifuge", "Thermal Analyzer", "Generic Analytical"],
                index=0,
                help="Equipment category for specialized content generation"
            )
            st.session_state.meta["author"] = st.text_input(
                "Author", 
                value=st.session_state.meta.get("author", ""),
                help="Document author"
            )
            st.session_state.meta["reviewer"] = st.text_input(
                "Technical Reviewer", 
                value=st.session_state.meta.get("reviewer", ""),
                help="Technical reviewer name"
            )
            st.session_state.meta["approver"] = st.text_input(
                "Approver", 
                value=st.session_state.meta.get("approver", ""),
                help="Document approver"
            )
    
    with st.expander("📁 Reference Documents", expanded=True):
        st.markdown("### Equipment Manuals & Technical Documents")
        uploads = st.file_uploader(
            "Upload reference documents", 
            type=["pdf", "docx", "xlsx", "xls", "txt"],
            accept_multiple_files=True,
            help="Upload equipment manuals, specifications, regulatory documents, and other references"
        )
        
        if uploads:
            tmpdir = tempfile.mkdtemp(prefix="sop_refs_")
            paths = []
            file_info = []
            
            for uf in uploads:
                p = os.path.join(tmpdir, uf.name)
                with open(p, "wb") as f:
                    f.write(uf.getbuffer())
                paths.append(p)
                file_info.append({
                    "name": uf.name,
                    "size": f"{uf.size / 1024:.1f} KB",
                    "type": uf.type or "Unknown"
                })
            
            st.session_state.uploaded_files = paths
            st.session_state.reference_documents = file_info
            
            # Display uploaded files
            st.success(f"✅ Uploaded {len(paths)} files")
            for info in file_info:
                st.write(f"📄 **{info['name']}** ({info['size']}, {info['type']})")
    
    # Professional validation settings
    with st.expander("⚙️ Generation Settings", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            validation_level = st.selectbox(
                "Validation Level",
                ["Professional", "Production Ready", "Basic"],
                index=0,
                help="Higher levels require more comprehensive validation"
            )
            st.session_state.validation_level = ValidationLevel.PROFESSIONAL if validation_level == "Professional" else \
                                             ValidationLevel.PRODUCTION_READY if validation_level == "Production Ready" else \
                                             ValidationLevel.BASIC
        
        with col2:
            max_iterations = st.slider(
                "Max Generation Iterations", 
                min_value=1, max_value=5, value=3,
                help="Maximum number of iterative improvements"
            )
            st.session_state.max_iterations = max_iterations
    
    # Add mandatory sections automatically
    if not st.session_state.mandatory_sections_added and st.button("🔧 Add Industry-Standard Sections"):
        from utils.section_validator import create_mandatory_sections_template
        mandatory_sections = create_mandatory_sections_template()
        st.session_state.sections.extend(mandatory_sections)
        st.session_state.mandatory_sections_added = True
        st.success("✅ Added 9 mandatory SOP sections according to industry standards")
        st.rerun()


def ui_professional_sections():
    """Enhanced section configuration with professional templates"""
    
    st.markdown("# 📝 Section Configuration")
    
    # Section management buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Add Custom Section"):
            st.session_state.sections.append({
                "title": f"Custom Section {len(st.session_state.sections)+1}",
                "mode": "ai",
                "prompt": "",
                "content": "",
                "order": len(st.session_state.sections) + 1
            })
            st.rerun()
    
    with col2:
        if st.button("📋 Add Mandatory Sections"):
            from utils.section_validator import create_mandatory_sections_template
            if not st.session_state.mandatory_sections_added:
                mandatory_sections = create_mandatory_sections_template()
                st.session_state.sections.extend(mandatory_sections)
                st.session_state.mandatory_sections_added = True
                st.success("✅ Added mandatory sections")
                st.rerun()
            else:
                st.info("Mandatory sections already added")
    
    with col3:
        if st.button("🗑️ Clear All Sections"):
            if st.checkbox("Confirm clear all sections"):
                st.session_state.sections = []
                st.session_state.mandatory_sections_added = False
                st.rerun()
    
    # Display current sections
    if st.session_state.sections:
        st.markdown(f"### Current Sections ({len(st.session_state.sections)})")
        
        for idx, section in enumerate(st.session_state.sections):
            with st.expander(f"{idx+1}. {section['title']}", expanded=False):
                
                # Section configuration
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    section["title"] = st.text_input(
                        "Section Title", 
                        value=section["title"], 
                        key=f"title_{idx}"
                    )
                
                with col2:
                    section["mode"] = st.selectbox(
                        "Generation Mode",
                        options=["ai", "ai+doc", "manual", "equipment_specific"],
                        index=["ai", "ai+doc", "manual", "equipment_specific"].index(
                            section.get("mode", "ai")
                        ),
                        key=f"mode_{idx}",
                        help="ai: AI-generated, ai+doc: AI with documents, manual: user-written, equipment_specific: specialized generation"
                    )
                
                # Mode-specific configurations
                if section["mode"] == "equipment_specific":
                    st.info("🔧 This section will use equipment-specific professional templates")
                    
                    section_types = [
                        "equipment_specifications", "operating_procedures", 
                        "calibration_procedures", "maintenance_procedures",
                        "safety_procedures", "troubleshooting", "quality_control"
                    ]
                    
                    section["section_type"] = st.selectbox(
                        "Section Type",
                        section_types,
                        index=section_types.index(section.get("section_type", "operating_procedures")),
                        key=f"section_type_{idx}"
                    )
                
                elif section["mode"] == "ai+doc":
                    st.markdown("📁 **Document Upload for This Section**")
                    uploads = st.file_uploader(
                        f"Documents for '{section['title']}'", 
                        type=["pdf", "docx", "xlsx", "xls", "txt"],
                        accept_multiple_files=True,
                        key=f"section_docs_{idx}",
                        help="Upload section-specific reference documents"
                    )
                    
                    if uploads:
                        tmpdir = tempfile.mkdtemp(prefix=f"sop_section_{idx}_")
                        paths = []
                        for uf in uploads:
                            p = os.path.join(tmpdir, uf.name)
                            with open(p, "wb") as f:
                                f.write(uf.getbuffer())
                            paths.append(p)
                        section["documents"] = paths
                        st.success(f"✅ Uploaded {len(paths)} files")
                
                elif section["mode"] == "manual":
                    section["content"] = st.text_area(
                        "Manual Content (Markdown supported)", 
                        value=section.get("content", ""), 
                        height=200, 
                        key=f"content_{idx}",
                        help="Write your own content using Markdown formatting"
                    )
                
                # Custom generation prompt
                section["prompt"] = st.text_area(
                    "Custom Generation Prompt (Optional)", 
                    value=section.get("prompt", ""), 
                    key=f"prompt_{idx}",
                    help="Provide specific instructions for AI generation of this section"
                )
                
                # Section reordering
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("⬆️ Move Up", key=f"up_{idx}") and idx > 0:
                        st.session_state.sections[idx], st.session_state.sections[idx-1] = \
                            st.session_state.sections[idx-1], st.session_state.sections[idx]
                        st.rerun()
                
                with col2:
                    if st.button("⬇️ Move Down", key=f"down_{idx}") and idx < len(st.session_state.sections) - 1:
                        st.session_state.sections[idx], st.session_state.sections[idx+1] = \
                            st.session_state.sections[idx+1], st.session_state.sections[idx]
                        st.rerun()
                
                with col3:
                    if st.button("🗑️ Delete", key=f"delete_{idx}"):
                        st.session_state.sections.pop(idx)
                        st.rerun()
                
                st.session_state.sections[idx] = section
    
    else:
        st.info("No sections configured. Add sections using the buttons above.")


def ui_professional_generation():
    """Enhanced generation interface with real-time monitoring"""
    
    st.markdown("# ⚡ Professional Generation")
    
    # Pre-generation validation
    validation_messages = []
    
    if not st.session_state.meta.get("title"):
        validation_messages.append("❌ SOP title is required")
    if not st.session_state.meta.get("number"):
        validation_messages.append("❌ SOP number is required")
    if not st.session_state.sections:
        validation_messages.append("❌ At least one section must be configured")
    
    if validation_messages:
        st.error("**Pre-generation Validation Failed:**")
        for msg in validation_messages:
            st.write(msg)
        st.stop()
    
    # Generation controls
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button(
            "🚀 Generate Professional SOP", 
            type="primary", 
            disabled=st.session_state.running,
            help="Start professional SOP generation with comprehensive validation"
        ):
            if st.session_state.worker and st.session_state.worker.is_alive():
                add_log("Generation already in progress. Please wait...")
            else:
                st.session_state.running = True
                t = threading.Thread(target=run_professional_generation_safe, daemon=True)
                add_script_run_ctx(t)
                st.session_state.worker = t
                t.start()
                st.rerun()
    
    with col2:
        if st.button("⏹️ Stop Generation", disabled=not st.session_state.running):
            st.session_state.running = False
            add_log("Generation stop requested")
    
    with col3:
        if st.button("🔄 Reset", help="Reset all generation data"):
            if st.checkbox("Confirm reset"):
                st.session_state.preview = []
                st.session_state.logs = []
                st.session_state.quality_assessment = None
                st.session_state.validation_result = None
                st.rerun()
    
    # Generation progress
    if st.session_state.running:
        st.info("🔄 Generation in progress... This may take several minutes.")
        
        progress_placeholder = st.empty()
        with progress_placeholder.container():
            progress_steps = [
                "Initializing professional systems",
                "Processing reference documents", 
                "Generating content with equipment-specific templates",
                "Conducting safety analysis",
                "Performing quality assessment",
                "Validating technical accuracy",
                "Final integration and formatting"
            ]
            
            # Simple progress estimation based on logs
            current_step = min(len(st.session_state.logs) // 3, len(progress_steps) - 1)
            st.progress(current_step / len(progress_steps))
            st.write(f"**Current Step:** {progress_steps[current_step]}")
    
    # Enhanced logging display
    st.markdown("### 📊 Generation Logs")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        log_level = st.radio("Log Level", ["All", "Important", "Errors"], horizontal=True)
    
    with col2:
        if st.button("📥 Download Logs"):
            log_content = "\n".join(st.session_state.logs)
            st.download_button(
                "Download Full Logs",
                log_content,
                file_name=f"sop_generation_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
    
    # Filter logs based on level
    filtered_logs = st.session_state.logs
    if log_level == "Important":
        filtered_logs = [log for log in st.session_state.logs 
                        if any(keyword in log.lower() for keyword in 
                              ["завершен", "одобрен", "ошибка", "валидация", "итерация"])]
    elif log_level == "Errors":
        filtered_logs = [log for log in st.session_state.logs if "ошибка" in log.lower()]
    
    # Display logs in a scrollable container
    with st.container():
        st.text_area(
            "Generation Logs", 
            value="\n".join(filtered_logs[-50:]),  # Last 50 logs
            height=300,
            disabled=True
        )
    
    # Real-time status updates
    if st.session_state.running:
        st.caption("🔄 Page will auto-refresh. Switch between tabs to see updates.")


def ui_professional_dashboard():
    """Professional readiness dashboard"""
    
    st.markdown("# 📊 SOP Readiness Dashboard")
    
    if not st.session_state.preview:
        st.info("No SOP content generated yet. Please generate content first.")
        return
    
    # Initialize dashboard
    dashboard = SOPReadinessDashboard()
    
    # Perform assessments if not done
    if not st.session_state.quality_assessment:
        perform_comprehensive_assessment()
    
    # Render main dashboard
    if st.session_state.quality_assessment:
        dashboard.render_main_dashboard(
            st.session_state.quality_assessment, 
            st.session_state.validation_result
        )
    
    # Additional professional insights
    if st.session_state.safety_analysis:
        st.markdown("---")
        with st.expander("🛡️ Safety Analysis Results", expanded=False):
            safety_score = st.session_state.safety_analysis.get("safety_integration_score", 0)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Safety Integration Score", f"{safety_score}/100")
            with col2:
                hazard_count = len(st.session_state.safety_analysis.get("hazard_analysis", []))
                st.metric("Identified Hazards", hazard_count)
            
            # Critical gaps
            gaps = st.session_state.safety_analysis.get("critical_safety_gaps", [])
            if gaps:
                st.markdown("**Critical Safety Gaps:**")
                for gap in gaps:
                    st.write(f"⚠️ {gap}")


def ui_professional_preview():
    """Enhanced preview with professional editing capabilities"""
    
    st.markdown("# 📋 Professional Preview & Export")
    
    if not st.session_state.preview:
        st.info("No content to preview. Generate SOP content first.")
        return
    
    # Content quality overview
    if st.session_state.quality_assessment:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            score = st.session_state.quality_assessment.overall_score
            st.metric("Overall Quality", f"{score}/100")
        
        with col2:
            status = st.session_state.quality_assessment.overall_status.value
            st.metric("Status", status)
        
        with col3:
            critical_count = len(st.session_state.quality_assessment.critical_issues)
            st.metric("Critical Issues", critical_count)
        
        with col4:
            if st.session_state.validation_result:
                level = st.session_state.validation_result.validation_level.value
                st.metric("Validation Level", level.title())
    
    # Section-by-section preview
    st.markdown("## 📝 Section Preview & Editing")
    
    for idx, section in enumerate(st.session_state.preview):
        with st.expander(f"{idx+1}. {section['title']}", expanded=False):
            
            # Content display tabs
            tab1, tab2 = st.tabs(["📖 Formatted View", "✏️ Edit Content"])
            
            with tab1:
                content = section.get("content", "")
                if content:
                    st.markdown(content, unsafe_allow_html=False)
                else:
                    st.write("*No content generated for this section*")
            
            with tab2:
                section["content"] = st.text_area(
                    "Edit Content (Markdown supported)",
                    value=section.get("content", ""),
                    height=300,
                    key=f"edit_content_{idx}",
                    help="Edit content using Markdown. Changes will be reflected in exports."
                )
                
                # Section-specific enhancement suggestions
                if st.button(f"🔧 Enhance Section", key=f"enhance_{idx}"):
                    # Placeholder for section enhancement
                    st.info("Section enhancement feature coming soon")
                
                st.session_state.preview[idx] = section
    
    # Export options
    st.markdown("## 📤 Professional Export Options")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📄 Export to Word"):
            try:
                doc, styles = load_template(os.path.join(os.path.dirname(__file__), "templates"))
                apply_styles(doc, styles)
                doc = populate_docx(doc, st.session_state.meta, st.session_state.preview)
                out_path = export_to_docx(doc, os.path.join(tempfile.gettempdir(), "professional_sop.docx"))
                
                with open(out_path, "rb") as f:
                    st.download_button(
                        "📥 Download DOCX",
                        f,
                        file_name=f"SOP_{st.session_state.meta.get('number', 'draft')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                st.success("✅ Word document generated successfully")
            except Exception as e:
                st.error(f"Error generating Word document: {e}")
    
    with col2:
        if st.button("📑 Export to PDF"):
            try:
                out_path = export_to_pdf(
                    st.session_state.preview, 
                    os.path.join(tempfile.gettempdir(), "professional_sop.pdf"),
                    st.session_state.meta
                )
                
                with open(out_path, "rb") as f:
                    st.download_button(
                        "📥 Download PDF",
                        f,
                        file_name=f"SOP_{st.session_state.meta.get('number', 'draft')}.pdf",
                        mime="application/pdf"
                    )
                st.success("✅ PDF document generated successfully")
            except Exception as e:
                st.error(f"Error generating PDF: {e}")
    
    with col3:
        if st.button("📊 Export Assessment"):
            if st.session_state.quality_assessment:
                assessment_data = {
                    "sop_title": st.session_state.meta.get("title"),
                    "sop_number": st.session_state.meta.get("number"),
                    "assessment_date": datetime.now().isoformat(),
                    "overall_score": st.session_state.quality_assessment.overall_score,
                    "overall_status": st.session_state.quality_assessment.overall_status.value,
                    "critical_issues": [
                        {
                            "section": issue.section,
                            "description": issue.description,
                            "suggestion": issue.improvement_suggestion
                        }
                        for issue in st.session_state.quality_assessment.critical_issues
                    ]
                }
                
                st.download_button(
                    "📥 Download Assessment",
                    json.dumps(assessment_data, indent=2, ensure_ascii=False),
                    file_name=f"SOP_Assessment_{st.session_state.meta.get('number', 'draft')}.json",
                    mime="application/json"
                )
            else:
                st.warning("No assessment data available")
    
    with col4:
        if st.button("📈 Save to History"):
            # Save current version to history
            version_data = {
                "version": st.session_state.current_version,
                "timestamp": datetime.now().isoformat(),
                "title": st.session_state.meta.get("title"),
                "number": st.session_state.meta.get("number"),
                "content": "\n\n".join([f"## {sec['title']}\n{sec.get('content', '')}" 
                                       for sec in st.session_state.preview]),
                "final_score": st.session_state.quality_assessment.overall_score if st.session_state.quality_assessment else 0,
                "status": st.session_state.quality_assessment.overall_status.value if st.session_state.quality_assessment else "Unknown",
                "iterations": st.session_state.max_iterations
            }
            
            st.session_state.sop_versions.append(version_data)
            st.session_state.generation_history.append(version_data)
            st.session_state.current_version += 1
            
            st.success(f"✅ Saved as Version {version_data['version']}")


def ui_metrics_dashboard():
    """Metrics and analytics dashboard"""
    
    metrics_dashboard = SOPMetricsDashboard()
    
    if st.session_state.generation_history:
        metrics_dashboard.render_metrics_dashboard(st.session_state.generation_history)
        
        # Version comparison if multiple versions exist
        if len(st.session_state.sop_versions) >= 2:
            st.markdown("---")
            render_comparison_dashboard(st.session_state.sop_versions)
    else:
        st.info("No generation history available. Generate some SOPs to see metrics and trends!")


def ui_improvement_engine():
    """Iterative Improvement Engine interface"""
    
    st.markdown("# 🔄 Iterative Improvement Engine")
    st.markdown("### Continuous Learning & Enhancement System")
    
    # User feedback section
    if st.session_state.current_document_id and not st.session_state.user_feedback_given:
        with st.expander("📝 Provide User Feedback", expanded=True):
            st.markdown("**Help us improve by providing feedback on the generated SOP:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                feedback_type = st.selectbox(
                    "Feedback Category",
                    ["quality", "accuracy", "completeness", "usability"],
                    help="Select the main aspect you're evaluating"
                )
                
                rating = st.slider(
                    "Overall Rating",
                    min_value=1, max_value=5, value=3,
                    help="1 = Poor, 5 = Excellent"
                )
                
                user_expertise = st.selectbox(
                    "Your Expertise Level",
                    ["beginner", "intermediate", "expert"],
                    index=1
                )
            
            with col2:
                specific_feedback = st.text_area(
                    "Specific Feedback",
                    height=100,
                    help="What specific issues did you notice?"
                )
                
                suggested_improvements = st.text_area(
                    "Suggested Improvements",
                    height=100,
                    help="How could this be improved?"
                )
            
            if st.button("📤 Submit Feedback", type="primary"):
                try:
                    st.session_state.improvement_engine.record_user_feedback(
                        document_id=st.session_state.current_document_id,
                        section_type="full_sop",
                        equipment_type=st.session_state.meta.get("equipment_type", "unknown"),
                        feedback_type=feedback_type,
                        rating=rating,
                        specific_feedback=specific_feedback,
                        suggested_improvements=suggested_improvements,
                        user_expertise=user_expertise
                    )
                    st.session_state.user_feedback_given = True
                    st.success("✅ Thank you! Your feedback has been recorded.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error recording feedback: {e}")
    
    # Performance dashboard
    st.markdown("## 📊 Performance Analytics")
    
    try:
        performance_data = st.session_state.improvement_engine.get_performance_dashboard_data()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Documents", 
                performance_data.get('total_documents', 0)
            )
        
        with col2:
            improvement_ops = performance_data.get('improvement_opportunities', 0)
            st.metric(
                "Improvement Opportunities", 
                improvement_ops,
                delta=f"+{improvement_ops}" if improvement_ops > 0 else None
            )
        
        with col3:
            if performance_data.get('quality_trend'):
                latest_quality = performance_data['quality_trend'][-1]['avg_quality']
                st.metric("Latest Quality Score", f"{latest_quality:.1f}/5.0")
        
        with col4:
            if performance_data.get('satisfaction_trend'):
                latest_satisfaction = performance_data['satisfaction_trend'][-1]['avg_rating']
                st.metric("User Satisfaction", f"{latest_satisfaction:.1f}/5.0")
        
        # Quality trend chart
        if performance_data.get('quality_trend'):
            st.markdown("### 📈 Quality Trend (Last 30 Days)")
            import plotly.graph_objects as go
            
            dates = [item['date'] for item in performance_data['quality_trend']]
            quality_scores = [item['avg_quality'] for item in performance_data['quality_trend']]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates, 
                y=quality_scores,
                mode='lines+markers',
                name='Quality Score',
                line=dict(color='#1f77b4', width=3)
            ))
            fig.update_layout(
                title="Quality Score Trend",
                xaxis_title="Date",
                yaxis_title="Average Quality Score",
                yaxis=dict(range=[0, 5])
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Equipment performance
        if performance_data.get('equipment_performance'):
            st.markdown("### 🔧 Equipment Performance Analysis")
            
            equipment_data = performance_data['equipment_performance']
            equipment_names = [item['equipment_type'] for item in equipment_data]
            equipment_scores = [item['avg_quality'] for item in equipment_data]
            document_counts = [item['document_count'] for item in equipment_data]
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = go.Figure(data=[
                    go.Bar(
                        x=equipment_names,
                        y=equipment_scores,
                        name='Average Quality Score',
                        marker_color='lightblue'
                    )
                ])
                fig.update_layout(
                    title="Quality by Equipment Type",
                    xaxis_title="Equipment Type",
                    yaxis_title="Average Quality Score"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = go.Figure(data=[
                    go.Bar(
                        x=equipment_names,
                        y=document_counts,
                        name='Document Count',
                        marker_color='lightgreen'
                    )
                ])
                fig.update_layout(
                    title="Documents Generated by Equipment Type",
                    xaxis_title="Equipment Type",
                    yaxis_title="Number of Documents"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        st.warning(f"Could not load performance data: {e}")
    
    # Improvement suggestions
    st.markdown("## 🚀 AI-Powered Improvement Suggestions")
    
    if st.button("🔍 Generate Improvement Report", type="primary"):
        with st.spinner("Analyzing patterns and generating suggestions..."):
            try:
                report = st.session_state.improvement_engine.generate_improvement_report()
                
                # Display summary
                summary = report.get('summary', {})
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Suggestions", summary.get('total_suggestions', 0))
                with col2:
                    st.metric("High Priority", summary.get('high_priority_count', 0))
                with col3:
                    st.metric("Expected Impact", f"{summary.get('expected_impact', 0):.2f}")
                
                # Display suggestions
                suggestions = report.get('improvement_suggestions', [])
                if suggestions:
                    st.markdown("### 🎯 Prioritized Improvement Suggestions")
                    
                    for i, suggestion in enumerate(suggestions[:10]):  # Show top 10
                        priority_color = "🔴" if suggestion['priority'] == 'high' else "🟡" if suggestion['priority'] == 'medium' else "🟢"
                        
                        with st.expander(f"{priority_color} {suggestion['target_component']}: {suggestion['description']}", expanded=i < 3):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write(f"**Priority:** {suggestion['priority'].upper()}")
                                st.write(f"**Type:** {suggestion['improvement_type']}")
                                st.write(f"**Expected Impact:** {suggestion['expected_impact']:.2f}")
                            
                            with col2:
                                st.write(f"**Implementation Effort:** {suggestion['implementation_effort']}")
                                st.write(f"**Target Component:** {suggestion['target_component']}")
                            
                            if suggestion.get('supporting_data'):
                                with st.expander("📊 Supporting Data"):
                                    st.json(suggestion['supporting_data'])
                
                # Validation improvements
                validation_improvements = report.get('validation_improvements', [])
                if validation_improvements:
                    st.markdown("### ✅ Validation System Improvements")
                    
                    for improvement in validation_improvements[:5]:
                        with st.expander(f"🔧 {improvement['target_component']}: {improvement['description']}"):
                            st.write(f"**Expected Impact:** {improvement['expected_impact']:.2f}")
                            st.write(f"**Effort:** {improvement['implementation_effort']}")
                            if improvement.get('supporting_data'):
                                st.json(improvement['supporting_data'])
                
                # Performance patterns
                patterns = report.get('performance_patterns', [])
                if patterns:
                    st.markdown("### 🔍 Identified Performance Patterns")
                    
                    for pattern in patterns[:3]:
                        st.warning(f"**{pattern['pattern_type'].replace('_', ' ').title()}:** {pattern['issue_description']}")
                        st.write(f"Frequency: {pattern['frequency']} occurrences")
                        st.write(f"Impact Score: {pattern['impact_score']:.2f}")
                        
                        if pattern.get('suggested_solutions'):
                            st.write("**Suggested Solutions:**")
                            for solution in pattern['suggested_solutions']:
                                st.write(f"• {solution}")
                
            except Exception as e:
                st.error(f"Error generating improvement report: {e}")
    
    # Prompt optimization
    st.markdown("## 📝 Prompt Optimization")
    
    equipment_types = ["Chromatography", "Spectroscopy", "Microscopy", "Analytical Balance", "Centrifuge"]
    selected_equipment = st.selectbox("Select Equipment Type for Optimization", equipment_types)
    
    if st.button("🔧 Generate Optimized Prompts"):
        with st.spinner("Analyzing feedback and optimizing prompts..."):
            try:
                optimized_prompts = st.session_state.improvement_engine.optimize_prompts_for_equipment(
                    selected_equipment.lower()
                )
                
                if optimized_prompts:
                    st.success(f"✅ Generated optimized prompts for {selected_equipment}")
                    
                    for section_type, prompt in optimized_prompts.items():
                        with st.expander(f"📋 {section_type.replace('_', ' ').title()} Section Prompt"):
                            st.text_area(
                                f"Optimized Prompt for {section_type}",
                                value=prompt,
                                height=200,
                                disabled=True
                            )
                            
                            if st.button(f"📋 Copy {section_type} Prompt", key=f"copy_{section_type}"):
                                st.code(prompt)
                else:
                    st.info(f"No specific optimization data available for {selected_equipment} yet. Generate more SOPs to build optimization data.")
            
            except Exception as e:
                st.error(f"Error optimizing prompts: {e}")
    
    # Data management
    st.markdown("---")
    st.markdown("## 🗃️ Data Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📤 Export Improvement Data"):
            try:
                report = st.session_state.improvement_engine.generate_improvement_report()
                
                st.download_button(
                    "📥 Download Improvement Report",
                    json.dumps(report, indent=2, ensure_ascii=False),
                    file_name=f"improvement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            except Exception as e:
                st.error(f"Error exporting data: {e}")
    
    with col2:
        if st.button("🗑️ Clear Analytics Data"):
            if st.checkbox("Confirm data clearing (this cannot be undone)"):
                try:
                    # Clear database (implementation would depend on specific needs)
                    st.warning("Data clearing functionality would be implemented based on requirements")
                except Exception as e:
                    st.error(f"Error clearing data: {e}")


def perform_comprehensive_assessment():
    """Perform comprehensive professional assessment"""
    
    if not st.session_state.preview:
        return
    
    # Combine all content for assessment
    full_content = "\n\n".join([
        f"## {section['title']}\n{section.get('content', '')}" 
        for section in st.session_state.preview
    ])
    
    try:
        # Quality assessment
        assessor = ProfessionalSOPAssessor()
        st.session_state.quality_assessment = assessor.perform_comprehensive_assessment(full_content)
        
        # Content validation
        validator = RealTimeContentValidator()
        st.session_state.validation_result = validator.validate_content_real_time(
            full_content,
            equipment_type=st.session_state.meta.get("equipment_type"),
            reference_documents=[section.get("content", "") for section in st.session_state.preview],
            validation_level=st.session_state.get("validation_level", ValidationLevel.PROFESSIONAL)
        )
        
        # Safety analysis
        safety_integrator = ProfessionalSafetyIntegrator()
        st.session_state.safety_analysis = safety_integrator.perform_comprehensive_safety_integration(
            full_content,
            equipment_type=st.session_state.meta.get("equipment_type")
        )
        
    except Exception as e:
        add_log(f"Assessment error: {e}")


def run_professional_generation_safe():
    """Safe wrapper for professional generation"""
    try:
        run_professional_generation()
    except Exception as e:
        add_log(f"Generation error: {e}")
    finally:
        st.session_state.running = False


def run_professional_generation():
    """Enhanced professional generation with all systems integrated"""
    
    add_log("🚀 Initializing professional SOP generation systems...")
    
    # Initialize all professional systems
    assessor = ProfessionalSOPAssessor()
    equipment_engine = ProfessionalEquipmentEngine()
    safety_integrator = ProfessionalSafetyIntegrator()
    validator = RealTimeContentValidator()
    
    # Initialize agents
    add_log("🤖 Building agent ensemble...")
    # NOTE: Professional app currently references additional agents (parser, styler, safety, quality).
    # The simplified two-agent flow changes in this commit do not modify this professional module.
    # Consider refactoring this file similarly if you intend to use it.
    coord = build_coordinator(on_log=add_log)
    sop_gen = build_sop_generator()
    doc_parser = build_document_parser()
    styler = build_content_styler()
    critic = build_critic()
    quality = build_quality_checker()
    safety = build_safety_agent()
    
    add_log("📚 Processing reference documents...")
    
    # Process all documents (global + section-specific)
    all_docs = st.session_state.uploaded_files.copy() if st.session_state.uploaded_files else []
    
    for section in st.session_state.sections:
        if section.get("mode") == "ai+doc" and section.get("documents"):
            all_docs.extend(section["documents"])
    
    chunks = parse_documents_to_chunks(all_docs)
    st.session_state.parsed_chunks = chunks
    corpus_summary = summarize_parsed_chunks(chunks)
    
    add_log(f"📄 Processed {len(all_docs)} reference documents, extracted {len(chunks)} content chunks")
    
    # Equipment-specific enhancements
    if st.session_state.meta.get("equipment_type"):
        add_log(f"🔧 Applying equipment-specific enhancements for {st.session_state.meta['equipment_type']}")
        
        # Identify equipment context
        ref_content = " ".join([chunk.get("text", "") for chunk in chunks])
        equipment_context = equipment_engine.extract_equipment_context(ref_content)
        add_log(f"📊 Extracted equipment context: {len(equipment_context.get('parameters', {}))} parameter types")
    
    def enhanced_instruction_builder(critique: str) -> str:
        """Enhanced instruction builder with professional requirements"""
        
        # Build base instruction
        base_instruction = build_generation_instruction(
            sop_title=st.session_state.meta["title"],
            sop_number=st.session_state.meta["number"],
            equipment_type=st.session_state.meta["equipment"],
            sections=st.session_state.sections,
            parsed_corpus_summary=corpus_summary if corpus_summary else None,
            critique_feedback=critique or None,
        )
        
        # Add professional enhancements
        professional_requirements = f"""

**PROFESSIONAL REQUIREMENTS (КРИТИЧЕСКОЕ СОБЛЮДЕНИЕ):**

1. **ТЕХНИЧЕСКАЯ ДЕТАЛИЗАЦИЯ:**
   - Все параметры должны иметь конкретные значения с единицами измерения
   - Указать допустимые диапазоны и критерии приемки
   - Включить настройки оборудования и конфигурации
   - Добавить процедуры самодиагностики

2. **ИНТЕГРАЦИЯ БЕЗОПАСНОСТИ:**
   - Встроить предупреждения **ВНИМАНИЕ** и **ПРЕДУПРЕЖДЕНИЕ** в критических точках
   - Указать конкретные СИЗ для каждой операции
   - Включить процедуры ЛОТО где применимо
   - Добавить аварийные процедуры и контакты

3. **НОРМАТИВНОЕ СООТВЕТСТВИЕ:**
   - Ссылки на ГОСТ, СанПиН, ISO с конкретными номерами разделов
   - Требования к документообороту и записям
   - Процедуры валидации и поверки

4. **ОПЕРАЦИОННАЯ ГОТОВНОСТЬ:**
   - Каждый шаг должен содержать критерии успешного выполнения
   - Процедуры устранения неисправностей
   - Временные рамки для операций
   - Контрольные точки качества

Документ должен быть готов к немедленному производственному использованию без дополнительных правок.
"""
        
        return base_instruction + professional_requirements
    
    add_log("🔄 Starting iterative generation with professional validation...")
    
    # Enhanced generation loop
    loop_result = iterative_generate_until_approved(
        coordinator=coord,
        sop_gen=sop_gen,
        safety=safety,
        critic=critic,
        quality=quality,
        styler=styler,
        base_instruction_builder=enhanced_instruction_builder,
        max_iters=st.session_state.max_iterations,
        logger=add_log,
    )
    
    add_log("📝 Processing generated content...")
    
    generated_content = loop_result.get("content", "")
    
    # Enhanced content processing for professional sections
    if st.session_state.meta.get("equipment_type") and generated_content:
        add_log("🔧 Applying equipment-specific content enhancements...")
        
        # Apply equipment-specific enhancements to sections
        enhanced_sections = []
        
        for section_config in st.session_state.sections:
            if section_config.get("mode") == "equipment_specific":
                # Use equipment engine for specialized content
                equipment_content = equipment_engine.generate_equipment_specific_content(
                    equipment_engine.identify_equipment_type(st.session_state.meta["equipment_type"]),
                    section_config.get("section_type", "operating_procedures"),
                    equipment_context if 'equipment_context' in locals() else {}
                )
                
                enhanced_sections.append({
                    "title": section_config["title"],
                    "content": equipment_content
                })
            elif section_config.get("mode") == "manual" and section_config.get("content"):
                enhanced_sections.append({
                    "title": section_config["title"],
                    "content": section_config["content"]
                })
            else:
                # Use generated content for AI modes
                enhanced_sections.append({
                    "title": section_config["title"],
                    "content": generated_content
                })
        
        st.session_state.preview = enhanced_sections
    else:
        # Standard section processing
        st.session_state.preview = [
            {
                "title": section_config["title"],
                "content": section_config.get("content") if section_config.get("mode") == "manual" 
                          else generated_content
            }
            for section_config in st.session_state.sections
        ]
    
    add_log("🔍 Performing comprehensive professional assessment...")
    
    # Comprehensive assessment
    perform_comprehensive_assessment()
    
    # Final status
    status = "✅ ОДОБРЕНО" if loop_result.get("approved") else "⚠️ ТРЕБУЮТСЯ ПРАВКИ"
    final_score = st.session_state.quality_assessment.overall_score if st.session_state.quality_assessment else 0
    
    add_log(f"🏁 Generation completed. Status: {status}, Quality Score: {final_score}/100")
    
    # Generate document ID and record metrics
    if st.session_state.preview:
        full_content = "\n\n".join([
            f"## {section['title']}\n{section.get('content', '')}" 
            for section in st.session_state.preview
        ])
        
        document_id = create_document_hash(full_content)
        st.session_state.current_document_id = document_id
        
        # Record generation metrics
        generation_time = 180.0  # Placeholder - could track actual time
        prompt_version = "professional_v1.0"
        
        st.session_state.improvement_engine.record_generation_session(
            document_id=document_id,
            content=full_content,
            equipment_type=st.session_state.meta.get("equipment_type", "unknown"),
            section_type="full_sop",
            generation_time=generation_time,
            prompt_version=prompt_version
        )
        
        add_log(f"📊 Recorded generation metrics for document {document_id[:8]}...")
    
    # Save to generation history
    history_entry = {
        "timestamp": datetime.now().isoformat(),
        "title": st.session_state.meta.get("title"),
        "number": st.session_state.meta.get("number"),
        "equipment_type": st.session_state.meta.get("equipment_type"),
        "final_score": final_score,
        "status": status,
        "iterations": st.session_state.max_iterations,
        "approved": loop_result.get("approved", False),
        "document_id": st.session_state.current_document_id
    }
    
    st.session_state.generation_history.append(history_entry)
    st.session_state.user_feedback_given = False  # Reset feedback flag


def main():
    """Main application entry point"""
    
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🔬",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    init_professional_session_state()
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("# 🔬 Professional SOP Generator")
        st.markdown("### Production-Grade System")
        
        page = st.radio(
            "Navigation",
            [
                "🏠 Setup & Configuration",
                "📝 Section Management", 
                "⚡ Generation",
                "📊 Readiness Dashboard",
                "📋 Preview & Export",
                "📈 Metrics & Analytics",
                "🔄 Improvement Engine"
            ]
        )
        
        st.markdown("---")
        
        # System status
        if st.session_state.preview:
            st.success("✅ SOP Content Generated")
        else:
            st.info("⏳ No Content Generated")
        
        if st.session_state.quality_assessment:
            score = st.session_state.quality_assessment.overall_score
            if score >= 95:
                st.success(f"🎯 Production Ready ({score}/100)")
            elif score >= 85:
                st.warning(f"⚠️ Review Required ({score}/100)")
            else:
                st.error(f"🚨 Major Revision Needed ({score}/100)")
        
        st.markdown("---")
        st.caption(f"Version: {st.session_state.current_version}")
        st.caption(f"Generated SOPs: {len(st.session_state.generation_history)}")
    
    # Main content area
    if page == "🏠 Setup & Configuration":
        ui_professional_home()
    elif page == "📝 Section Management":
        ui_professional_sections()
    elif page == "⚡ Generation":
        ui_professional_generation()
    elif page == "📊 Readiness Dashboard":
        ui_professional_dashboard()
    elif page == "📋 Preview & Export":
        ui_professional_preview()
    elif page == "📈 Metrics & Analytics":
        ui_metrics_dashboard()
    elif page == "🔄 Improvement Engine":
        ui_improvement_engine()


if __name__ == "__main__":
    main()