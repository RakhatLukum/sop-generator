#!/usr/bin/env python3
"""
Iterative Improvement Engine for SOP Generation System

This module implements a comprehensive improvement engine that learns from user feedback,
document usage patterns, and generation quality to continuously enhance the SOP generation process.
"""

import json
import sqlite3
import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import statistics
from collections import defaultdict, Counter
import hashlib

from .quality_assessment import ProfessionalSOPAssessor, SOPReadinessAssessment
from .equipment_engine import EquipmentType, ProfessionalEquipmentEngine
from .advanced_prompts import SectionType, AdvancedPromptEngine


@dataclass
class UserFeedback:
    """User feedback on generated content"""
    document_id: str
    section_type: str
    equipment_type: str
    feedback_type: str  # 'quality', 'accuracy', 'completeness', 'usability'
    rating: int  # 1-5 scale
    specific_feedback: str
    suggested_improvements: str
    timestamp: datetime.datetime
    user_expertise_level: str  # 'beginner', 'intermediate', 'expert'


@dataclass
class GenerationMetrics:
    """Metrics for generated content performance"""
    document_id: str
    generation_time: float
    quality_score: float
    user_satisfaction: float
    usage_frequency: int
    revision_count: int
    final_approval_rate: float
    equipment_type: str
    section_type: str
    prompt_version: str
    timestamp: datetime.datetime


@dataclass
class ImprovementSuggestion:
    """Suggested improvements based on analysis"""
    improvement_type: str  # 'prompt_optimization', 'template_enhancement', 'validation_rule'
    priority: str  # 'high', 'medium', 'low'
    target_component: str
    description: str
    expected_impact: float
    implementation_effort: str
    supporting_data: Dict[str, Any]


@dataclass
class PerformancePattern:
    """Identified performance patterns"""
    pattern_type: str
    equipment_types: List[str]
    section_types: List[str]
    issue_description: str
    frequency: int
    impact_score: float
    suggested_solutions: List[str]


class FeedbackDatabase:
    """Database manager for feedback and metrics storage"""
    
    def __init__(self, db_path: str = "sop_improvement.db"):
        self.db_path = db_path
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the feedback database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    section_type TEXT NOT NULL,
                    equipment_type TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    specific_feedback TEXT,
                    suggested_improvements TEXT,
                    timestamp TEXT NOT NULL,
                    user_expertise_level TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS generation_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    generation_time REAL NOT NULL,
                    quality_score REAL NOT NULL,
                    user_satisfaction REAL DEFAULT 0,
                    usage_frequency INTEGER DEFAULT 0,
                    revision_count INTEGER DEFAULT 0,
                    final_approval_rate REAL DEFAULT 0,
                    equipment_type TEXT NOT NULL,
                    section_type TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS improvement_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    improvement_type TEXT NOT NULL,
                    target_component TEXT NOT NULL,
                    description TEXT NOT NULL,
                    implementation_date TEXT NOT NULL,
                    impact_before REAL,
                    impact_after REAL,
                    success_rate REAL
                )
            """)
    
    def store_feedback(self, feedback: UserFeedback):
        """Store user feedback in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO user_feedback 
                (document_id, section_type, equipment_type, feedback_type, rating, 
                 specific_feedback, suggested_improvements, timestamp, user_expertise_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                feedback.document_id, feedback.section_type, feedback.equipment_type,
                feedback.feedback_type, feedback.rating, feedback.specific_feedback,
                feedback.suggested_improvements, feedback.timestamp.isoformat(),
                feedback.user_expertise_level
            ))
    
    def store_metrics(self, metrics: GenerationMetrics):
        """Store generation metrics in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO generation_metrics 
                (document_id, generation_time, quality_score, user_satisfaction,
                 usage_frequency, revision_count, final_approval_rate, equipment_type,
                 section_type, prompt_version, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.document_id, metrics.generation_time, metrics.quality_score,
                metrics.user_satisfaction, metrics.usage_frequency, metrics.revision_count,
                metrics.final_approval_rate, metrics.equipment_type, metrics.section_type,
                metrics.prompt_version, metrics.timestamp.isoformat()
            ))
    
    def get_feedback_by_equipment(self, equipment_type: str) -> List[Dict]:
        """Get feedback data for specific equipment type"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM user_feedback WHERE equipment_type = ?
                ORDER BY timestamp DESC
            """, (equipment_type,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_metrics_by_section(self, section_type: str) -> List[Dict]:
        """Get metrics data for specific section type"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM generation_metrics WHERE section_type = ?
                ORDER BY timestamp DESC
            """, (section_type,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_performance_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get performance trends over specified time period"""
        cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Quality trends
            quality_cursor = conn.execute("""
                SELECT AVG(quality_score) as avg_quality, equipment_type, section_type
                FROM generation_metrics 
                WHERE timestamp >= ?
                GROUP BY equipment_type, section_type
            """, (cutoff_date,))
            
            # Satisfaction trends
            satisfaction_cursor = conn.execute("""
                SELECT AVG(rating) as avg_satisfaction, equipment_type, section_type
                FROM user_feedback 
                WHERE timestamp >= ?
                GROUP BY equipment_type, section_type
            """, (cutoff_date,))
            
            return {
                'quality_trends': [dict(row) for row in quality_cursor.fetchall()],
                'satisfaction_trends': [dict(row) for row in satisfaction_cursor.fetchall()]
            }


class PatternAnalyzer:
    """Analyzes patterns in feedback and performance data"""
    
    def __init__(self, database: FeedbackDatabase):
        self.database = database
    
    def identify_low_performance_areas(self, threshold: float = 3.0) -> List[PerformancePattern]:
        """Identify areas with consistently low performance"""
        patterns = []
        
        # Analyze quality scores by equipment and section
        with sqlite3.connect(self.database.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT equipment_type, section_type, 
                       AVG(quality_score) as avg_quality,
                       COUNT(*) as frequency
                FROM generation_metrics 
                GROUP BY equipment_type, section_type
                HAVING avg_quality < ? AND frequency >= 5
            """, (threshold,))
            
            for row in cursor.fetchall():
                pattern = PerformancePattern(
                    pattern_type="low_quality",
                    equipment_types=[row['equipment_type']],
                    section_types=[row['section_type']],
                    issue_description=f"Consistently low quality scores ({row['avg_quality']:.2f})",
                    frequency=row['frequency'],
                    impact_score=5.0 - row['avg_quality'],
                    suggested_solutions=[
                        "Enhance prompt templates",
                        "Add more equipment-specific guidance",
                        "Improve validation rules"
                    ]
                )
                patterns.append(pattern)
        
        return patterns
    
    def identify_common_feedback_themes(self) -> Dict[str, List[str]]:
        """Identify common themes in user feedback"""
        with sqlite3.connect(self.database.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT specific_feedback, suggested_improvements, equipment_type, section_type
                FROM user_feedback 
                WHERE rating <= 3
            """)
            
            themes = defaultdict(list)
            common_words = Counter()
            
            for row in cursor.fetchall():
                feedback_text = f"{row['specific_feedback']} {row['suggested_improvements']}"
                words = feedback_text.lower().split()
                
                # Filter meaningful words (simple approach)
                meaningful_words = [w for w in words if len(w) > 4 and w not in ['should', 'could', 'would', 'better']]
                common_words.update(meaningful_words)
                
                key = f"{row['equipment_type']}_{row['section_type']}"
                themes[key].append(feedback_text)
        
        # Return most common themes
        return {
            'common_issues': common_words.most_common(20),
            'feedback_by_context': dict(themes)
        }
    
    def analyze_prompt_effectiveness(self) -> Dict[str, float]:
        """Analyze effectiveness of different prompt versions"""
        with sqlite3.connect(self.database.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT prompt_version, AVG(quality_score) as avg_quality,
                       AVG(user_satisfaction) as avg_satisfaction,
                       COUNT(*) as usage_count
                FROM generation_metrics 
                GROUP BY prompt_version
                HAVING usage_count >= 3
            """)
            
            effectiveness = {}
            for row in cursor.fetchall():
                composite_score = (row['avg_quality'] * 0.7 + row['avg_satisfaction'] * 0.3)
                effectiveness[row['prompt_version']] = {
                    'composite_score': composite_score,
                    'quality_score': row['avg_quality'],
                    'satisfaction_score': row['avg_satisfaction'],
                    'usage_count': row['usage_count']
                }
        
        return effectiveness


class ImprovementRecommendationEngine:
    """Generates specific improvement recommendations"""
    
    def __init__(self, database: FeedbackDatabase, pattern_analyzer: PatternAnalyzer):
        self.database = database
        self.pattern_analyzer = pattern_analyzer
    
    def generate_improvement_suggestions(self) -> List[ImprovementSuggestion]:
        """Generate prioritized improvement suggestions"""
        suggestions = []
        
        # Analyze low-performance patterns
        patterns = self.pattern_analyzer.identify_low_performance_areas()
        for pattern in patterns:
            if pattern.impact_score > 1.5:  # High impact threshold
                suggestion = ImprovementSuggestion(
                    improvement_type="prompt_optimization",
                    priority="high" if pattern.impact_score > 2.0 else "medium",
                    target_component=f"{pattern.equipment_types[0]}_{pattern.section_types[0]}",
                    description=f"Optimize prompts for {pattern.equipment_types[0]} {pattern.section_types[0]} sections",
                    expected_impact=pattern.impact_score * 0.4,
                    implementation_effort="medium",
                    supporting_data={
                        'current_quality': 5.0 - pattern.impact_score,
                        'frequency': pattern.frequency,
                        'pattern_type': pattern.pattern_type
                    }
                )
                suggestions.append(suggestion)
        
        # Analyze prompt effectiveness
        prompt_effectiveness = self.pattern_analyzer.analyze_prompt_effectiveness()
        if prompt_effectiveness:
            best_prompts = sorted(prompt_effectiveness.items(), 
                                key=lambda x: x[1]['composite_score'], reverse=True)
            worst_prompts = sorted(prompt_effectiveness.items(), 
                                 key=lambda x: x[1]['composite_score'])
            
            if len(worst_prompts) > 0 and worst_prompts[0][1]['composite_score'] < 3.5:
                suggestion = ImprovementSuggestion(
                    improvement_type="template_enhancement",
                    priority="high",
                    target_component=worst_prompts[0][0],
                    description=f"Enhance template based on successful patterns from {best_prompts[0][0] if best_prompts else 'higher-performing versions'}",
                    expected_impact=1.2,
                    implementation_effort="low",
                    supporting_data={
                        'current_score': worst_prompts[0][1]['composite_score'],
                        'target_score': best_prompts[0][1]['composite_score'] if best_prompts else 4.0
                    }
                )
                suggestions.append(suggestion)
        
        # Sort by priority and expected impact
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        suggestions.sort(key=lambda x: (priority_order[x.priority], x.expected_impact), reverse=True)
        
        return suggestions
    
    def recommend_validation_improvements(self) -> List[ImprovementSuggestion]:
        """Recommend improvements to validation rules"""
        suggestions = []
        
        # Analyze cases where quality scores don't match user satisfaction
        with sqlite3.connect(self.database.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT m.equipment_type, m.section_type, 
                       AVG(m.quality_score) as avg_quality,
                       AVG(f.rating) as avg_satisfaction,
                       COUNT(*) as count
                FROM generation_metrics m
                JOIN user_feedback f ON m.document_id = f.document_id
                GROUP BY m.equipment_type, m.section_type
                HAVING count >= 3 AND ABS(avg_quality - avg_satisfaction) > 1.0
            """)
            
            for row in cursor.fetchall():
                gap = abs(row['avg_quality'] - row['avg_satisfaction'])
                if gap > 1.0:
                    suggestion = ImprovementSuggestion(
                        improvement_type="validation_rule",
                        priority="medium",
                        target_component=f"validation_{row['equipment_type']}_{row['section_type']}",
                        description=f"Improve validation alignment between quality assessment and user satisfaction",
                        expected_impact=gap * 0.3,
                        implementation_effort="medium",
                        supporting_data={
                            'quality_score': row['avg_quality'],
                            'satisfaction_score': row['avg_satisfaction'],
                            'gap': gap,
                            'sample_size': row['count']
                        }
                    )
                    suggestions.append(suggestion)
        
        return suggestions


class IterativeImprovementEngine:
    """Main improvement engine that coordinates all improvement activities"""
    
    def __init__(self, db_path: str = "sop_improvement.db"):
        self.database = FeedbackDatabase(db_path)
        self.pattern_analyzer = PatternAnalyzer(self.database)
        self.recommendation_engine = ImprovementRecommendationEngine(
            self.database, self.pattern_analyzer
        )
        self.assessor = ProfessionalSOPAssessor()
        self.equipment_engine = ProfessionalEquipmentEngine()
        self.prompt_engine = AdvancedPromptEngine()
    
    def record_generation_session(self, document_id: str, content: str, 
                                equipment_type: str, section_type: str,
                                generation_time: float, prompt_version: str) -> GenerationMetrics:
        """Record metrics from a generation session"""
        
        # Assess quality
        assessment = self.assessor.assess_sop_readiness(content)
        quality_score = assessment.overall_score
        
        metrics = GenerationMetrics(
            document_id=document_id,
            generation_time=generation_time,
            quality_score=quality_score,
            user_satisfaction=0,  # Will be updated when feedback is received
            usage_frequency=1,
            revision_count=0,
            final_approval_rate=1.0 if quality_score >= 80 else 0.0,
            equipment_type=equipment_type,
            section_type=section_type,
            prompt_version=prompt_version,
            timestamp=datetime.datetime.now()
        )
        
        self.database.store_metrics(metrics)
        return metrics
    
    def record_user_feedback(self, document_id: str, section_type: str,
                           equipment_type: str, feedback_type: str,
                           rating: int, specific_feedback: str,
                           suggested_improvements: str,
                           user_expertise: str = "intermediate") -> UserFeedback:
        """Record user feedback"""
        
        feedback = UserFeedback(
            document_id=document_id,
            section_type=section_type,
            equipment_type=equipment_type,
            feedback_type=feedback_type,
            rating=rating,
            specific_feedback=specific_feedback,
            suggested_improvements=suggested_improvements,
            timestamp=datetime.datetime.now(),
            user_expertise_level=user_expertise
        )
        
        self.database.store_feedback(feedback)
        
        # Update corresponding metrics
        self._update_metrics_with_feedback(document_id, rating)
        
        return feedback
    
    def _update_metrics_with_feedback(self, document_id: str, rating: int):
        """Update metrics with user satisfaction data"""
        with sqlite3.connect(self.database.db_path) as conn:
            conn.execute("""
                UPDATE generation_metrics 
                SET user_satisfaction = ?
                WHERE document_id = ?
            """, (rating, document_id))
    
    def generate_improvement_report(self) -> Dict[str, Any]:
        """Generate comprehensive improvement report"""
        
        suggestions = self.recommendation_engine.generate_improvement_suggestions()
        validation_improvements = self.recommendation_engine.recommend_validation_improvements()
        patterns = self.pattern_analyzer.identify_low_performance_areas()
        themes = self.pattern_analyzer.identify_common_feedback_themes()
        trends = self.database.get_performance_trends(30)
        
        return {
            'improvement_suggestions': [asdict(s) for s in suggestions],
            'validation_improvements': [asdict(s) for s in validation_improvements],
            'performance_patterns': [asdict(p) for p in patterns],
            'feedback_themes': themes,
            'performance_trends': trends,
            'summary': {
                'total_suggestions': len(suggestions) + len(validation_improvements),
                'high_priority_count': len([s for s in suggestions if s.priority == 'high']),
                'expected_impact': sum(s.expected_impact for s in suggestions),
                'generated_at': datetime.datetime.now().isoformat()
            }
        }
    
    def optimize_prompts_for_equipment(self, equipment_type: str) -> Dict[str, str]:
        """Generate optimized prompts based on feedback analysis"""
        
        # Get feedback for this equipment type
        feedback_data = self.database.get_feedback_by_equipment(equipment_type)
        
        if not feedback_data:
            return {}
        
        # Analyze common issues
        low_rating_feedback = [f for f in feedback_data if f['rating'] <= 3]
        common_issues = []
        
        for feedback in low_rating_feedback:
            issues = feedback.get('specific_feedback', '') + ' ' + feedback.get('suggested_improvements', '')
            common_issues.append(issues)
        
        # Generate enhanced prompts based on issues
        optimized_prompts = {}
        
        for section_type in ['purpose_scope', 'safety_risk', 'procedure', 'troubleshooting']:
            base_prompt = self.prompt_engine.generate_section_prompt(
                section_type=section_type,
                equipment_category=equipment_type,
                technical_requirements=["Address common user issues"],
                safety_requirements=["Enhanced safety focus based on feedback"],
                regulatory_requirements=["Improved regulatory compliance"],
                quality_criteria=["Higher technical detail", "Better clarity"]
            )
            
            # Enhance based on common issues
            enhancement_notes = f"\n\nIMPORTANT IMPROVEMENTS BASED ON USER FEEDBACK:\n"
            if 'technical' in str(common_issues).lower():
                enhancement_notes += "- Provide more specific technical parameters and values\n"
            if 'procedure' in str(common_issues).lower():
                enhancement_notes += "- Include more detailed step-by-step procedures\n"
            if 'safety' in str(common_issues).lower():
                enhancement_notes += "- Enhance safety considerations and precautions\n"
            if 'example' in str(common_issues).lower():
                enhancement_notes += "- Include specific examples and case studies\n"
            
            optimized_prompts[section_type] = base_prompt + enhancement_notes
        
        return optimized_prompts
    
    def get_performance_dashboard_data(self) -> Dict[str, Any]:
        """Get data for performance dashboard"""
        
        # Get recent performance trends
        trends = self.database.get_performance_trends(30)
        
        # Calculate key metrics
        with sqlite3.connect(self.database.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Overall quality trend
            quality_cursor = conn.execute("""
                SELECT DATE(timestamp) as date, AVG(quality_score) as avg_quality
                FROM generation_metrics 
                WHERE timestamp >= date('now', '-30 days')
                GROUP BY DATE(timestamp)
                ORDER BY date
            """)
            quality_trend = [dict(row) for row in quality_cursor.fetchall()]
            
            # User satisfaction trend
            satisfaction_cursor = conn.execute("""
                SELECT DATE(timestamp) as date, AVG(rating) as avg_rating
                FROM user_feedback 
                WHERE timestamp >= date('now', '-30 days')
                GROUP BY DATE(timestamp)
                ORDER BY date
            """)
            satisfaction_trend = [dict(row) for row in satisfaction_cursor.fetchall()]
            
            # Equipment performance
            equipment_cursor = conn.execute("""
                SELECT equipment_type, AVG(quality_score) as avg_quality,
                       COUNT(*) as document_count
                FROM generation_metrics
                WHERE timestamp >= date('now', '-30 days')
                GROUP BY equipment_type
            """)
            equipment_performance = [dict(row) for row in equipment_cursor.fetchall()]
        
        return {
            'quality_trend': quality_trend,
            'satisfaction_trend': satisfaction_trend,
            'equipment_performance': equipment_performance,
            'improvement_opportunities': len(self.recommendation_engine.generate_improvement_suggestions()),
            'total_documents': len(quality_trend) if quality_trend else 0
        }


def create_document_hash(content: str) -> str:
    """Create a unique hash for document content"""
    return hashlib.md5(content.encode()).hexdigest()[:12]