from typing import Dict, List, Any, Optional
import streamlit as st
# Optional plotly imports for dashboard components
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("Warning: Dashboard visualizations disabled due to missing plotly dependency")
import pandas as pd
from datetime import datetime

from ..utils.quality_assessment import SOPReadinessAssessment, SOPReadinessLevel, IssueLevel
from ..utils.content_validator import ContentValidationResult, ValidationLevel


class SOPReadinessDashboard:
    """Professional SOP readiness dashboard for production-grade assessment"""
    
    def __init__(self):
        self.colors = {
            "production_ready": "#28a745",
            "review_required": "#ffc107", 
            "major_revision": "#dc3545",
            "critical": "#dc3545",
            "warning": "#ffc107",
            "suggestion": "#17a2b8",
            "excellent": "#28a745",
            "good": "#20c997",
            "fair": "#ffc107",
            "poor": "#fd7e14",
            "critical_low": "#dc3545"
        }
    
    def render_main_dashboard(self, assessment: SOPReadinessAssessment, validation_result: ContentValidationResult = None):
        """Render the main SOP readiness dashboard"""
        
        # Dashboard header
        st.markdown("# 📊 SOP READINESS ASSESSMENT")
        st.markdown("---")
        
        # Overall status section
        self._render_overall_status(assessment)
        
        # Metrics overview
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self._render_category_scores(assessment)
        
        with col2:
            self._render_issue_summary(assessment)
        
        st.markdown("---")
        
        # Detailed sections
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 Detailed Analysis", 
            "⚠️ Issues & Recommendations", 
            "🔍 Validation Results",
            "📋 Action Plan"
        ])
        
        with tab1:
            self._render_detailed_analysis(assessment)
        
        with tab2:
            self._render_issues_and_recommendations(assessment)
        
        with tab3:
            if validation_result:
                self._render_validation_results(validation_result)
            else:
                st.info("Run content validation for detailed technical analysis")
        
        with tab4:
            self._render_action_plan(assessment, validation_result)
    
    def _render_overall_status(self, assessment: SOPReadinessAssessment):
        """Render overall status section"""
        
        # Status indicator
        status_colors = {
            SOPReadinessLevel.PRODUCTION_READY: self.colors["production_ready"],
            SOPReadinessLevel.REVIEW_REQUIRED: self.colors["review_required"],
            SOPReadinessLevel.MAJOR_REVISION_NEEDED: self.colors["major_revision"]
        }
        
        status_icons = {
            SOPReadinessLevel.PRODUCTION_READY: "✅",
            SOPReadinessLevel.REVIEW_REQUIRED: "⚠️",
            SOPReadinessLevel.MAJOR_REVISION_NEEDED: "❌"
        }
        
        status_color = status_colors.get(assessment.overall_status, self.colors["major_revision"])
        status_icon = status_icons.get(assessment.overall_status, "❌")
        
        # Main status display
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown(f"""
            <div style="text-align: center; padding: 20px; border-radius: 10px; 
                       background-color: {status_color}; color: white; margin: 20px 0;">
                <h1 style="margin: 0; font-size: 2.5em;">{status_icon}</h1>
                <h2 style="margin: 10px 0; color: white;">{assessment.overall_status.value}</h2>
                <h3 style="margin: 0; color: white;">Overall Score: {assessment.overall_score}/100</h3>
            </div>
            """, unsafe_allow_html=True)
        
        # Score interpretation
        if assessment.overall_score >= 95:
            st.success("🎉 Document is ready for immediate production use!")
        elif assessment.overall_score >= 85:
            st.warning("📝 Document requires minor improvements before production use")
        elif assessment.overall_score >= 70:
            st.warning("🔧 Document needs significant improvements")
        else:
            st.error("🚨 Document requires major revision before use")
    
    def _render_category_scores(self, assessment: SOPReadinessAssessment):
        """Render category scores with radar chart"""
        
        st.subheader("📊 Category Performance")
        
        # Prepare data for radar chart
        categories = [
            "Technical Completeness",
            "Safety Coverage", 
            "Operational Clarity",
            "Regulatory Compliance",
            "Professional Standards"
        ]
        
        scores = [
            assessment.technical_completeness.score,
            assessment.safety_coverage.score,
            assessment.operational_clarity.score,
            assessment.regulatory_compliance.score,
            assessment.professional_standards.score
        ]
        
        # Create radar chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=scores,
            theta=categories,
            fill='toself',
            name='Current Score',
            line_color=self.colors["fair"]
        ))
        
        # Add target score line
        target_scores = [90] * len(categories)
        fig.add_trace(go.Scatterpolar(
            r=target_scores,
            theta=categories,
            fill='toself',
            name='Production Target',
            opacity=0.3,
            line_color=self.colors["production_ready"]
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )),
            showlegend=True,
            title="Score vs Production Target",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Category details table
        st.subheader("📋 Category Details")
        
        category_data = []
        for i, category in enumerate(categories):
            score = scores[i]
            status = "✅ Excellent" if score >= 90 else "⚠️ Needs Work" if score >= 70 else "❌ Critical"
            category_data.append({
                "Category": category,
                "Score": f"{score}/100",
                "Status": status,
                "Gap to Target": f"{max(0, 90 - score)} points"
            })
        
        df = pd.DataFrame(category_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    def _render_issue_summary(self, assessment: SOPReadinessAssessment):
        """Render issue summary with metrics"""
        
        st.subheader("🎯 Issue Summary")
        
        critical_count = len(assessment.critical_issues)
        warning_count = len(assessment.warnings)
        suggestion_count = len(assessment.suggestions)
        
        # Issue metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="❌ Critical Issues",
                value=critical_count,
                delta=f"-{critical_count}" if critical_count > 0 else "None",
                delta_color="inverse"
            )
        
        with col2:
            st.metric(
                label="⚠️ Warnings", 
                value=warning_count,
                delta=f"-{warning_count}" if warning_count > 0 else "None",
                delta_color="inverse"
            )
        
        with col3:
            st.metric(
                label="💡 Suggestions",
                value=suggestion_count,
                delta=f"{suggestion_count} items" if suggestion_count > 0 else "None"
            )
        
        # Issue distribution chart
        if critical_count + warning_count + suggestion_count > 0:
            fig = go.Figure(data=[
                go.Pie(
                    labels=['Critical', 'Warnings', 'Suggestions'],
                    values=[critical_count, warning_count, suggestion_count],
                    marker_colors=[self.colors["critical"], self.colors["warning"], self.colors["suggestion"]],
                    hole=0.4
                )
            ])
            
            fig.update_layout(
                title="Issue Distribution",
                showlegend=True,
                height=300,
                margin=dict(t=40, b=0, l=0, r=0)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Priority actions
        if critical_count > 0:
            st.error(f"🚨 {critical_count} critical issues must be resolved before production use")
        elif warning_count > 0:
            st.warning(f"⚠️ {warning_count} warnings should be addressed")
        else:
            st.success("✅ No critical issues detected")
    
    def _render_detailed_analysis(self, assessment: SOPReadinessAssessment):
        """Render detailed analysis section"""
        
        st.subheader("🔍 Detailed Category Analysis")
        
        categories = [
            ("Technical Completeness", assessment.technical_completeness),
            ("Safety Coverage", assessment.safety_coverage),
            ("Operational Clarity", assessment.operational_clarity),
            ("Regulatory Compliance", assessment.regulatory_compliance),
            ("Professional Standards", assessment.professional_standards)
        ]
        
        for category_name, category_score in categories:
            with st.expander(f"📊 {category_name} - {category_score.score}/100"):
                
                # Score visualization
                progress_color = self._get_progress_color(category_score.score)
                st.markdown(f"""
                <div style="background-color: #f0f0f0; border-radius: 10px; padding: 10px; margin: 10px 0;">
                    <div style="background-color: {progress_color}; height: 20px; border-radius: 5px; 
                               width: {category_score.score}%; text-align: center; color: white; line-height: 20px;">
                        {category_score.score}/100
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Category issues
                if category_score.issues:
                    st.write("**Issues identified:**")
                    for issue in category_score.issues:
                        issue_icon = "❌" if issue.level.value == "CRITICAL" else "⚠️" if issue.level.value == "WARNING" else "💡"
                        st.write(f"{issue_icon} **{issue.section}**: {issue.description}")
                        if issue.improvement_suggestion:
                            st.write(f"   💡 *Suggestion*: {issue.improvement_suggestion}")
                        st.write("")
                else:
                    st.success("✅ No issues identified in this category")
    
    def _render_issues_and_recommendations(self, assessment: SOPReadinessAssessment):
        """Render issues and recommendations section"""
        
        st.subheader("⚠️ Issues and Recommendations")
        
        # Critical issues
        if assessment.critical_issues:
            st.markdown("### ❌ Critical Issues (Must Fix)")
            for i, issue in enumerate(assessment.critical_issues, 1):
                with st.container():
                    st.markdown(f"""
                    <div style="border-left: 4px solid {self.colors['critical']}; padding: 10px; margin: 10px 0; 
                               background-color: rgba(220, 53, 69, 0.1);">
                        <strong>#{i} {issue.section}</strong><br>
                        {issue.description}<br>
                        <em>💡 Recommendation: {issue.improvement_suggestion}</em>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Warnings
        if assessment.warnings:
            st.markdown("### ⚠️ Warnings (Should Fix)")
            for i, issue in enumerate(assessment.warnings[:10], 1):  # Limit to first 10
                with st.container():
                    st.markdown(f"""
                    <div style="border-left: 4px solid {self.colors['warning']}; padding: 10px; margin: 10px 0; 
                               background-color: rgba(255, 193, 7, 0.1);">
                        <strong>#{i} {issue.section}</strong><br>
                        {issue.description}<br>
                        <em>💡 Recommendation: {issue.improvement_suggestion}</em>
                    </div>
                    """, unsafe_allow_html=True)
            
            if len(assessment.warnings) > 10:
                st.info(f"... and {len(assessment.warnings) - 10} more warnings")
        
        # Suggestions
        if assessment.suggestions:
            st.markdown("### 💡 Suggestions (Nice to Have)")
            with st.expander(f"View {len(assessment.suggestions)} suggestions"):
                for i, issue in enumerate(assessment.suggestions, 1):
                    st.write(f"**{i}. {issue.section}**: {issue.description}")
                    if issue.improvement_suggestion:
                        st.write(f"   *Suggestion*: {issue.improvement_suggestion}")
                    st.write("")
    
    def _render_validation_results(self, validation_result: ContentValidationResult):
        """Render validation results section"""
        
        st.subheader("🔍 Content Validation Results")
        
        # Validation level achieved
        level_colors = {
            ValidationLevel.PRODUCTION_READY: self.colors["production_ready"],
            ValidationLevel.PROFESSIONAL: self.colors["good"],
            ValidationLevel.BASIC: self.colors["warning"]
        }
        
        level_color = level_colors.get(validation_result.validation_level, self.colors["warning"])
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"""
            <div style="text-align: center; padding: 15px; border-radius: 8px; 
                       background-color: {level_color}; color: white;">
                <h3 style="margin: 0; color: white;">Validation Level Achieved</h3>
                <h2 style="margin: 5px 0; color: white;">{validation_result.validation_level.value.upper()}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Validation scores
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Technical Accuracy", f"{validation_result.technical_accuracy_score:.0f}/100")
        with col2:
            st.metric("Completeness", f"{validation_result.completeness_score:.0f}/100")
        with col3:
            st.metric("Safety", f"{validation_result.safety_score:.0f}/100")
        with col4:
            st.metric("Regulatory", f"{validation_result.regulatory_score:.0f}/100")
        
        # Enhancement suggestions
        if validation_result.enhancement_suggestions:
            st.subheader("🚀 Enhancement Opportunities")
            
            for suggestion in validation_result.enhancement_suggestions:
                priority_colors = {
                    "critical": self.colors["critical"],
                    "high": self.colors["warning"],
                    "medium": self.colors["fair"],
                    "low": self.colors["suggestion"]
                }
                
                priority_color = priority_colors.get(suggestion["priority"], self.colors["suggestion"])
                
                st.markdown(f"""
                <div style="border-left: 4px solid {priority_color}; padding: 10px; margin: 10px 0; 
                           background-color: rgba(128, 128, 128, 0.05);">
                    <strong>{suggestion['title']}</strong> 
                    <span style="background-color: {priority_color}; color: white; padding: 2px 8px; 
                                 border-radius: 12px; font-size: 0.8em;">{suggestion['priority'].upper()}</span><br>
                    {suggestion['description']}<br>
                    <em>🎯 Action: {suggestion['action']}</em>
                </div>
                """, unsafe_allow_html=True)
        
        # Missing sections
        if validation_result.missing_sections:
            st.subheader("📝 Missing Required Sections")
            for section in validation_result.missing_sections:
                st.write(f"• {section}")
    
    def _render_action_plan(self, assessment: SOPReadinessAssessment, validation_result: ContentValidationResult = None):
        """Render action plan section"""
        
        st.subheader("📋 Recommended Action Plan")
        
        # Determine priority actions based on assessment
        actions = []
        
        # Critical issues first
        if assessment.critical_issues:
            actions.append({
                "priority": 1,
                "title": "🚨 Resolve Critical Issues",
                "description": f"Address {len(assessment.critical_issues)} critical issues that prevent production use",
                "timeframe": "Immediate",
                "effort": "High"
            })
        
        # Missing sections
        if validation_result and validation_result.missing_sections:
            actions.append({
                "priority": 2,
                "title": "📝 Add Missing Sections", 
                "description": f"Add {len(validation_result.missing_sections)} required sections",
                "timeframe": "1-2 days",
                "effort": "Medium"
            })
        
        # Technical accuracy
        if validation_result and validation_result.technical_accuracy_score < 80:
            actions.append({
                "priority": 2,
                "title": "🔧 Improve Technical Accuracy",
                "description": "Enhance technical parameters and specifications",
                "timeframe": "1-3 days",
                "effort": "Medium"
            })
        
        # Safety improvements
        if assessment.safety_coverage.score < 85:
            actions.append({
                "priority": 2,
                "title": "🛡️ Strengthen Safety Measures",
                "description": "Integrate comprehensive safety procedures",
                "timeframe": "1-2 days", 
                "effort": "Medium"
            })
        
        # Warnings and suggestions
        if assessment.warnings:
            actions.append({
                "priority": 3,
                "title": "⚠️ Address Warnings",
                "description": f"Resolve {len(assessment.warnings)} warnings for improved quality",
                "timeframe": "2-5 days",
                "effort": "Low-Medium"
            })
        
        # Final review
        actions.append({
            "priority": 4,
            "title": "✅ Final Review and Approval",
            "description": "Conduct final review and obtain approval for production use",
            "timeframe": "1 day",
            "effort": "Low"
        })
        
        # Render action plan table
        if actions:
            action_data = []
            for action in actions:
                action_data.append({
                    "Priority": action["priority"],
                    "Action": action["title"],
                    "Description": action["description"],
                    "Timeframe": action["timeframe"],
                    "Effort": action["effort"]
                })
            
            df = pd.DataFrame(action_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Time estimate
        if assessment.overall_score < 70:
            st.error("⏱️ **Estimated time to production ready**: 5-10 business days")
        elif assessment.overall_score < 85:
            st.warning("⏱️ **Estimated time to production ready**: 2-5 business days")
        else:
            st.success("⏱️ **Estimated time to production ready**: 1-2 business days")
    
    def _get_progress_color(self, score: int) -> str:
        """Get color based on score"""
        if score >= 90:
            return self.colors["excellent"]
        elif score >= 80:
            return self.colors["good"]
        elif score >= 70:
            return self.colors["fair"]
        elif score >= 60:
            return self.colors["poor"]
        else:
            return self.colors["critical_low"]


class SOPMetricsDashboard:
    """Dashboard for tracking SOP generation metrics and trends"""
    
    def __init__(self):
        self.colors = SOPReadinessDashboard().colors
    
    def render_metrics_dashboard(self, generation_history: List[Dict[str, Any]]):
        """Render SOP generation metrics dashboard"""
        
        st.markdown("# 📈 SOP Generation Metrics")
        st.markdown("---")
        
        if not generation_history:
            st.info("No generation history available. Generate some SOPs to see metrics!")
            return
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(generation_history)
        df['date'] = pd.to_datetime(df['timestamp'])
        
        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total SOPs Generated", len(df))
        
        with col2:
            production_ready = len(df[df['final_score'] >= 95])
            st.metric("Production Ready", production_ready, 
                     delta=f"{(production_ready/len(df)*100):.1f}% of total")
        
        with col3:
            avg_score = df['final_score'].mean()
            st.metric("Average Quality Score", f"{avg_score:.1f}")
        
        with col4:
            avg_iterations = df['iterations'].mean()
            st.metric("Avg Iterations", f"{avg_iterations:.1f}")
        
        # Quality trends
        st.subheader("📊 Quality Trends Over Time")
        
        fig = px.line(df, x='date', y='final_score', 
                     title="SOP Quality Score Over Time",
                     labels={'final_score': 'Quality Score', 'date': 'Date'})
        fig.add_hline(y=95, line_dash="dash", line_color="green", 
                     annotation_text="Production Ready Threshold")
        fig.add_hline(y=85, line_dash="dash", line_color="orange",
                     annotation_text="Review Required Threshold")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Equipment type analysis
        if 'equipment_type' in df.columns:
            st.subheader("🔧 Performance by Equipment Type")
            
            equipment_stats = df.groupby('equipment_type').agg({
                'final_score': ['mean', 'count'],
                'iterations': 'mean'
            }).round(1)
            
            equipment_stats.columns = ['Avg Score', 'Count', 'Avg Iterations']
            st.dataframe(equipment_stats, use_container_width=True)
        
        # Issue patterns
        if 'common_issues' in df.columns:
            st.subheader("⚠️ Common Issue Patterns")
            
            all_issues = []
            for issues_list in df['common_issues'].dropna():
                if isinstance(issues_list, list):
                    all_issues.extend(issues_list)
            
            if all_issues:
                issue_counts = pd.Series(all_issues).value_counts().head(10)
                
                fig = px.bar(x=issue_counts.values, y=issue_counts.index,
                           orientation='h', title="Most Common Issues")
                fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                
                st.plotly_chart(fig, use_container_width=True)


def render_comparison_dashboard(sop_versions: List[Dict[str, Any]]):
    """Render comparison dashboard for multiple SOP versions"""
    
    st.markdown("# 🔄 SOP Version Comparison")
    st.markdown("---")
    
    if len(sop_versions) < 2:
        st.info("Need at least 2 SOP versions to show comparison")
        return
    
    # Version selector
    col1, col2 = st.columns(2)
    
    with col1:
        version_1 = st.selectbox("Select Version 1", 
                                [f"Version {i+1} ({v['timestamp']})" for i, v in enumerate(sop_versions)])
        v1_idx = int(version_1.split()[1]) - 1
    
    with col2:
        version_2 = st.selectbox("Select Version 2",
                                [f"Version {i+1} ({v['timestamp']})" for i, v in enumerate(sop_versions)])
        v2_idx = int(version_2.split()[1]) - 1
    
    if v1_idx != v2_idx:
        v1 = sop_versions[v1_idx]
        v2 = sop_versions[v2_idx]
        
        # Score comparison
        st.subheader("📊 Score Comparison")
        
        categories = ['Technical', 'Safety', 'Operational', 'Regulatory', 'Professional']
        v1_scores = [v1.get(f'{cat.lower()}_score', 0) for cat in categories]
        v2_scores = [v2.get(f'{cat.lower()}_score', 0) for cat in categories]
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=v1_scores, theta=categories, fill='toself', name='Version 1'))
        fig.add_trace(go.Scatterpolar(r=v2_scores, theta=categories, fill='toself', name='Version 2'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Improvement summary
        improvements = []
        for i, category in enumerate(categories):
            diff = v2_scores[i] - v1_scores[i]
            if abs(diff) > 1:  # Only show significant changes
                direction = "↗️" if diff > 0 else "↘️"
                improvements.append(f"{direction} {category}: {diff:+.1f} points")
        
        if improvements:
            st.subheader("📈 Key Changes")
            for improvement in improvements:
                st.write(f"• {improvement}")
        
        # Content diff (simplified)
        st.subheader("📝 Content Changes")
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_area("Version 1 Content Preview", v1.get('content', '')[:500] + "...", height=200, disabled=True)
        with col2:
            st.text_area("Version 2 Content Preview", v2.get('content', '')[:500] + "...", height=200, disabled=True)