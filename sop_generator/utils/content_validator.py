from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re
import json
from pathlib import Path

from .quality_assessment import ProfessionalSOPAssessor, SOPReadinessAssessment
from .equipment_engine import ProfessionalEquipmentEngine, EquipmentType
from .safety_integration import ProfessionalSafetyIntegrator


class ValidationLevel(Enum):
    BASIC = "basic"
    PROFESSIONAL = "professional"
    PRODUCTION_READY = "production_ready"


class ContentIssueType(Enum):
    TECHNICAL_ACCURACY = "technical_accuracy"
    COMPLETENESS = "completeness"
    INDUSTRY_STANDARDS = "industry_standards"
    SAFETY_COMPLIANCE = "safety_compliance"
    REGULATORY_COMPLIANCE = "regulatory_compliance"


@dataclass
class ValidationIssue:
    issue_type: ContentIssueType
    severity: str  # "critical", "major", "minor"
    section: str
    line_number: Optional[int]
    description: str
    current_content: str
    suggested_improvement: str
    reference_source: Optional[str] = None
    regulatory_requirement: Optional[str] = None


@dataclass
class ContentValidationResult:
    overall_score: float
    validation_level: ValidationLevel
    issues: List[ValidationIssue]
    enhancement_suggestions: List[Dict[str, Any]]
    missing_sections: List[str]
    technical_accuracy_score: float
    completeness_score: float
    safety_score: float
    regulatory_score: float


class RealTimeContentValidator:
    """Real-time SOP content validation and enhancement system"""
    
    def __init__(self):
        self.quality_assessor = ProfessionalSOPAssessor()
        self.equipment_engine = ProfessionalEquipmentEngine()
        self.safety_integrator = ProfessionalSafetyIntegrator()
        
        # Load validation patterns and references
        self.technical_patterns = self._load_technical_validation_patterns()
        self.industry_standards = self._load_industry_standards()
        self.reference_materials = self._load_reference_materials()
    
    def _load_technical_validation_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load technical validation patterns for accuracy checking"""
        return {
            "parameter_validation": {
                "temperature": {
                    "patterns": [r'(\d+(?:\.\d+)?)\s*[°℃]\s*[CF]?'],
                    "typical_ranges": {
                        "ambient": (15, 30),
                        "elevated": (40, 200),
                        "high": (200, 1000)
                    },
                    "validation_rules": [
                        "Must include units",
                        "Must specify tolerance if critical",
                        "Must be within equipment capabilities"
                    ]
                },
                "pressure": {
                    "patterns": [r'(\d+(?:\.\d+)?)\s*(?:бар|bar|кПа|МПа|атм|psi)'],
                    "typical_ranges": {
                        "atmospheric": (0.8, 1.2),
                        "low_pressure": (1, 10),
                        "high_pressure": (10, 600)
                    },
                    "validation_rules": [
                        "Must include units",
                        "Must specify safety limits",
                        "Must include pressure relief information for high pressure"
                    ]
                },
                "flow_rate": {
                    "patterns": [r'(\d+(?:\.\d+)?)\s*(?:мл/мин|ml/min|л/мин|L/min)'],
                    "typical_ranges": {
                        "analytical": (0.1, 5.0),
                        "preparative": (5, 50),
                        "process": (50, 1000)
                    },
                    "validation_rules": [
                        "Must include units",
                        "Must be compatible with column specifications",
                        "Must consider back-pressure limits"
                    ]
                }
            },
            "procedure_validation": {
                "step_numbering": {
                    "pattern": r'^\d+\.\s+',
                    "requirements": ["Sequential numbering", "Clear action verbs", "Measurable outcomes"]
                },
                "decision_points": {
                    "pattern": r'если\s+.*,\s*то|в\s+случае\s+если|при\s+(?:превышении|отклонении)',
                    "requirements": ["Clear conditions", "Specific actions", "Escalation procedures"]
                },
                "success_criteria": {
                    "pattern": r'критерий\s+(?:успеха|выполнения|приемки)',
                    "requirements": ["Quantifiable metrics", "Acceptance ranges", "Verification methods"]
                }
            },
            "safety_validation": {
                "hazard_identification": {
                    "required_elements": ["Risk assessment", "Control measures", "PPE requirements", "Emergency procedures"],
                    "patterns": [r'опасность|риск|hazard', r'СИЗ|PPE|защит', r'аварий|emergency']
                },
                "regulatory_compliance": {
                    "required_standards": ["ГОСТ", "СанПиН", "ISO", "OSHA"],
                    "patterns": [r'ГОСТ\s+[\d.-]+', r'ISO\s+\d+', r'СанПиН\s+[\d.]+']
                }
            }
        }
    
    def _load_industry_standards(self) -> Dict[str, Dict[str, Any]]:
        """Load industry standards database for validation"""
        return {
            "ISO_17025": {
                "title": "General requirements for the competence of testing and calibration laboratories",
                "sections": {
                    "7.2": "Selection, verification and validation of methods",
                    "7.3": "Sampling",
                    "7.4": "Handling of test or calibration items",
                    "7.7": "Ensuring the validity of results"
                },
                "required_elements": [
                    "Method validation parameters",
                    "Uncertainty estimation",
                    "Quality control procedures",
                    "Traceability requirements"
                ]
            },
            "ICH_Q2": {
                "title": "Validation of Analytical Procedures",
                "sections": {
                    "1": "Introduction", 
                    "2": "Types of Analytical Procedures",
                    "3": "Validation Characteristics",
                    "4": "Analytical Procedure Validation"
                },
                "required_elements": [
                    "Accuracy assessment",
                    "Precision evaluation",
                    "Linearity and range",
                    "Detection and quantitation limits",
                    "Robustness testing"
                ]
            },
            "GMP": {
                "title": "Good Manufacturing Practice",
                "sections": {
                    "2": "Quality Management",
                    "3": "Personnel",
                    "4": "Premises and Equipment",
                    "6": "Quality Control"
                },
                "required_elements": [
                    "Documentation control",
                    "Change control procedures",
                    "Deviation handling",
                    "CAPA system integration"
                ]
            }
        }
    
    def _load_reference_materials(self) -> Dict[str, List[str]]:
        """Load reference materials for content enhancement"""
        return {
            "equipment_manuals": [
                "Manufacturer operation manuals",
                "Maintenance and service guides",
                "Troubleshooting references",
                "Software user guides"
            ],
            "regulatory_guidance": [
                "FDA guidance documents",
                "EMA guidelines",
                "ICH harmonized tripartite guidelines",
                "National pharmacopeias"
            ],
            "industry_publications": [
                "Peer-reviewed journal articles",
                "Industry best practice guides",
                "Professional society standards",
                "Technical application notes"
            ]
        }
    
    def validate_content_real_time(self, 
                                 sop_content: str,
                                 equipment_type: str = None,
                                 reference_documents: List[str] = None,
                                 validation_level: ValidationLevel = ValidationLevel.PROFESSIONAL) -> ContentValidationResult:
        """Perform real-time content validation with enhancement suggestions"""
        
        issues = []
        enhancement_suggestions = []
        
        # Technical accuracy validation
        technical_issues, technical_score = self._validate_technical_accuracy(sop_content, equipment_type, reference_documents)
        issues.extend(technical_issues)
        
        # Completeness validation
        completeness_issues, completeness_score, missing_sections = self._validate_completeness(sop_content)
        issues.extend(completeness_issues)
        
        # Industry standards compliance
        standards_issues, standards_score = self._validate_industry_standards(sop_content, validation_level)
        issues.extend(standards_issues)
        
        # Safety compliance validation
        safety_issues, safety_score = self._validate_safety_compliance(sop_content, equipment_type)
        issues.extend(safety_issues)
        
        # Generate enhancement suggestions
        enhancements = self._generate_enhancement_suggestions(sop_content, issues, reference_documents)
        enhancement_suggestions.extend(enhancements)
        
        # Calculate overall score
        overall_score = (technical_score * 0.3 + completeness_score * 0.25 + 
                        standards_score * 0.20 + safety_score * 0.25)
        
        # Determine validation level achieved
        achieved_level = self._determine_validation_level(overall_score, issues)
        
        return ContentValidationResult(
            overall_score=overall_score,
            validation_level=achieved_level,
            issues=issues,
            enhancement_suggestions=enhancement_suggestions,
            missing_sections=missing_sections,
            technical_accuracy_score=technical_score,
            completeness_score=completeness_score,
            safety_score=safety_score,
            regulatory_score=standards_score
        )
    
    def _validate_technical_accuracy(self, 
                                   content: str, 
                                   equipment_type: str = None,
                                   reference_docs: List[str] = None) -> Tuple[List[ValidationIssue], float]:
        """Validate technical accuracy against reference materials"""
        
        issues = []
        score = 100.0
        
        # Parameter validation
        param_patterns = self.technical_patterns["parameter_validation"]
        
        for param_type, config in param_patterns.items():
            for pattern in config["patterns"]:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                
                for match in matches:
                    value_str = match.group(1)
                    try:
                        value = float(value_str)
                        
                        # Check if value is within reasonable ranges
                        ranges = config["typical_ranges"]
                        in_range = False
                        
                        for range_type, (min_val, max_val) in ranges.items():
                            if min_val <= value <= max_val:
                                in_range = True
                                break
                        
                        if not in_range:
                            issues.append(ValidationIssue(
                                issue_type=ContentIssueType.TECHNICAL_ACCURACY,
                                severity="major",
                                section=f"Параметр {param_type}",
                                line_number=self._get_line_number(content, match.start()),
                                description=f"Значение {param_type} ({value}) может быть некорректным",
                                current_content=match.group(0),
                                suggested_improvement=f"Проверить соответствие типичным диапазонам для {param_type}",
                                reference_source="Technical validation patterns"
                            ))
                            score -= 5
                    
                    except ValueError:
                        issues.append(ValidationIssue(
                            issue_type=ContentIssueType.TECHNICAL_ACCURACY,
                            severity="minor",
                            section=f"Параметр {param_type}",
                            line_number=self._get_line_number(content, match.start()),
                            description=f"Некорректный формат значения {param_type}",
                            current_content=match.group(0),
                            suggested_improvement="Использовать числовой формат с единицами измерения"
                        ))
                        score -= 2
        
        # Cross-reference validation with equipment specifications
        if equipment_type and reference_docs:
            equipment_issues, eq_score_deduction = self._cross_reference_equipment_specs(
                content, equipment_type, reference_docs)
            issues.extend(equipment_issues)
            score -= eq_score_deduction
        
        # Procedure logic validation
        procedure_issues, proc_score_deduction = self._validate_procedure_logic(content)
        issues.extend(procedure_issues)
        score -= proc_score_deduction
        
        return issues, max(score, 0)
    
    def _validate_completeness(self, content: str) -> Tuple[List[ValidationIssue], float, List[str]]:
        """Validate completeness against mandatory sections"""
        
        issues = []
        missing_sections = []
        score = 100.0
        
        # Use quality assessor for comprehensive completeness check
        assessment = self.quality_assessor.perform_comprehensive_assessment(content)
        
        # Convert assessment issues to validation issues
        for category_score in [assessment.technical_completeness, assessment.safety_coverage,
                             assessment.operational_clarity, assessment.regulatory_compliance,
                             assessment.professional_standards]:
            
            for issue in category_score.issues:
                severity_map = {"CRITICAL": "critical", "WARNING": "major", "SUGGESTION": "minor"}
                
                validation_issue = ValidationIssue(
                    issue_type=ContentIssueType.COMPLETENESS,
                    severity=severity_map.get(issue.level.value, "minor"),
                    section=issue.section,
                    line_number=None,
                    description=issue.description,
                    current_content="",
                    suggested_improvement=issue.improvement_suggestion
                )
                issues.append(validation_issue)
        
        # Extract missing sections
        found_sections, missing = self.quality_assessor.validate_section_presence(content)
        missing_sections = missing
        
        # Calculate completeness score
        total_sections = len(found_sections) + len(missing_sections)
        if total_sections > 0:
            score = (len(found_sections) / total_sections) * 100
        
        return issues, score, missing_sections
    
    def _validate_industry_standards(self, content: str, validation_level: ValidationLevel) -> Tuple[List[ValidationIssue], float]:
        """Validate against industry standards"""
        
        issues = []
        score = 100.0
        
        # Check for required standard references
        required_standards = []
        
        if validation_level in [ValidationLevel.PROFESSIONAL, ValidationLevel.PRODUCTION_READY]:
            required_standards.extend(["ISO 17025", "ICH Q2"])
        
        if validation_level == ValidationLevel.PRODUCTION_READY:
            required_standards.extend(["GMP", "21 CFR"])
        
        content_lower = content.lower()
        
        for standard in required_standards:
            standard_patterns = [
                standard.lower().replace(" ", r"\s*"),
                standard.replace(" ", ""),
                standard.replace(" ", "-")
            ]
            
            found = False
            for pattern in standard_patterns:
                if re.search(pattern, content_lower):
                    found = True
                    break
            
            if not found:
                issues.append(ValidationIssue(
                    issue_type=ContentIssueType.INDUSTRY_STANDARDS,
                    severity="major",
                    section="Нормативные ссылки",
                    line_number=None,
                    description=f"Отсутствует ссылка на стандарт {standard}",
                    current_content="",
                    suggested_improvement=f"Добавить ссылку на стандарт {standard} в соответствующий раздел",
                    regulatory_requirement=standard
                ))
                score -= 15
        
        # Check for specific standard requirements
        for standard_key, standard_info in self.industry_standards.items():
            if any(std_name in content_lower for std_name in [standard_key.lower(), standard_info["title"].lower()]):
                # Standard is referenced, check for required elements
                missing_elements = []
                
                for element in standard_info["required_elements"]:
                    element_keywords = element.lower().split()
                    if not any(keyword in content_lower for keyword in element_keywords):
                        missing_elements.append(element)
                
                if missing_elements:
                    issues.append(ValidationIssue(
                        issue_type=ContentIssueType.INDUSTRY_STANDARDS,
                        severity="major",
                        section=f"Соответствие {standard_key}",
                        line_number=None,
                        description=f"Не выполнены требования стандарта: {', '.join(missing_elements)}",
                        current_content="",
                        suggested_improvement=f"Добавить разделы/процедуры для: {', '.join(missing_elements)}",
                        regulatory_requirement=standard_key
                    ))
                    score -= 10
        
        return issues, max(score, 0)
    
    def _validate_safety_compliance(self, content: str, equipment_type: str = None) -> Tuple[List[ValidationIssue], float]:
        """Validate safety compliance"""
        
        issues = []
        score = 100.0
        
        # Use safety integrator for comprehensive safety validation
        try:
            safety_analysis = self.safety_integrator.perform_comprehensive_safety_integration(
                content, equipment_type)
            
            # Convert safety gaps to validation issues
            for gap in safety_analysis.get("critical_safety_gaps", []):
                issues.append(ValidationIssue(
                    issue_type=ContentIssueType.SAFETY_COMPLIANCE,
                    severity="critical",
                    section="Безопасность",
                    line_number=None,
                    description=gap,
                    current_content="",
                    suggested_improvement="Добавить соответствующие процедуры безопасности"
                ))
                score -= 20
            
            # Check safety integration score
            safety_score = safety_analysis.get("safety_integration_score", 70)
            if safety_score < 80:
                issues.append(ValidationIssue(
                    issue_type=ContentIssueType.SAFETY_COMPLIANCE,
                    severity="major",
                    section="Интеграция безопасности",
                    line_number=None,
                    description="Недостаточная интеграция мер безопасности в процедуры",
                    current_content="",
                    suggested_improvement="Усилить интеграцию требований безопасности во все этапы процедуры"
                ))
                score -= 15
        
        except Exception as e:
            # Fallback validation
            basic_safety_issues, basic_score_deduction = self._basic_safety_validation(content)
            issues.extend(basic_safety_issues)
            score -= basic_score_deduction
        
        return issues, max(score, 0)
    
    def _basic_safety_validation(self, content: str) -> Tuple[List[ValidationIssue], float]:
        """Basic safety validation as fallback"""
        
        issues = []
        score_deduction = 0
        
        safety_requirements = {
            "PPE requirements": [r'сиз|защитн.*средств|перчатк|очк', "Требования к СИЗ не указаны"],
            "Emergency procedures": [r'аварий|чрезвычай|экстрен', "Отсутствуют аварийные процедуры"],
            "Hazard identification": [r'опасность|риск|вредн', "Не проведена идентификация опасностей"],
            "Regulatory compliance": [r'гост|санпин|iso', "Отсутствуют ссылки на стандарты безопасности"]
        }
        
        content_lower = content.lower()
        
        for requirement, (pattern, description) in safety_requirements.items():
            if not re.search(pattern, content_lower):
                issues.append(ValidationIssue(
                    issue_type=ContentIssueType.SAFETY_COMPLIANCE,
                    severity="major",
                    section="Безопасность",
                    line_number=None,
                    description=description,
                    current_content="",
                    suggested_improvement=f"Добавить раздел: {requirement}"
                ))
                score_deduction += 15
        
        return issues, score_deduction
    
    def _cross_reference_equipment_specs(self, 
                                       content: str, 
                                       equipment_type: str,
                                       reference_docs: List[str]) -> Tuple[List[ValidationIssue], float]:
        """Cross-reference content against equipment specifications"""
        
        issues = []
        score_deduction = 0
        
        # Identify equipment type and get specifications
        try:
            eq_type = self.equipment_engine.identify_equipment_type(equipment_type, reference_docs)
            
            # Extract context from reference documents
            context = {}
            for doc in reference_docs:
                doc_context = self.equipment_engine.extract_equipment_context(doc)
                # Merge contexts
                for key, value in doc_context.items():
                    if key not in context:
                        context[key] = value
                    elif isinstance(value, list):
                        context[key].extend(value)
            
            # Check if SOP parameters match equipment capabilities
            if context.get("parameters"):
                content_params = self._extract_parameters_from_content(content)
                
                for content_param, content_values in content_params.items():
                    if content_param in context["parameters"]:
                        ref_values = context["parameters"][content_param]
                        
                        # Simple validation - can be enhanced
                        if not self._parameters_match(content_values, ref_values):
                            issues.append(ValidationIssue(
                                issue_type=ContentIssueType.TECHNICAL_ACCURACY,
                                severity="major",
                                section="Технические параметры",
                                line_number=None,
                                description=f"Параметр {content_param} может не соответствовать характеристикам оборудования",
                                current_content=str(content_values),
                                suggested_improvement="Проверить соответствие техническим характеристикам оборудования",
                                reference_source="Equipment documentation"
                            ))
                            score_deduction += 5
        
        except Exception as e:
            # Log error but don't fail validation
            pass
        
        return issues, score_deduction
    
    def _validate_procedure_logic(self, content: str) -> Tuple[List[ValidationIssue], float]:
        """Validate logical flow and completeness of procedures"""
        
        issues = []
        score_deduction = 0
        
        # Check for step numbering consistency
        step_pattern = r'^\s*(\d+)\.\s+'
        step_matches = list(re.finditer(step_pattern, content, re.MULTILINE))
        
        if len(step_matches) > 1:
            expected_num = 1
            for match in step_matches:
                actual_num = int(match.group(1))
                if actual_num != expected_num:
                    issues.append(ValidationIssue(
                        issue_type=ContentIssueType.COMPLETENESS,
                        severity="minor",
                        section="Нумерация шагов",
                        line_number=self._get_line_number(content, match.start()),
                        description=f"Нарушена последовательность нумерации: ожидался шаг {expected_num}, найден {actual_num}",
                        current_content=match.group(0),
                        suggested_improvement="Исправить нумерацию шагов"
                    ))
                    score_deduction += 1
                expected_num += 1
        
        # Check for decision points and branching logic
        decision_patterns = [
            r'если\s+.*,\s*то',
            r'в\s+случае\s+если',
            r'при\s+(?:превышении|отклонении|несоответствии)'
        ]
        
        decision_matches = 0
        for pattern in decision_patterns:
            decision_matches += len(re.findall(pattern, content, re.IGNORECASE))
        
        if decision_matches > 0:
            # Check if each decision point has clear outcomes
            unclear_decisions = re.findall(r'если\s+[^,]{5,50},\s*то\s*[^\.]{0,20}[\.\n]', content, re.IGNORECASE)
            
            for unclear in unclear_decisions:
                issues.append(ValidationIssue(
                    issue_type=ContentIssueType.COMPLETENESS,
                    severity="major",
                    section="Логика процедур",
                    line_number=None,
                    description="Неясно определены действия при принятии решения",
                    current_content=unclear.strip(),
                    suggested_improvement="Четко определить действия для каждого исхода решения"
                ))
                score_deduction += 3
        
        return issues, score_deduction
    
    def _generate_enhancement_suggestions(self, 
                                        content: str, 
                                        issues: List[ValidationIssue],
                                        reference_docs: List[str] = None) -> List[Dict[str, Any]]:
        """Generate content enhancement suggestions"""
        
        suggestions = []
        
        # Analyze issue patterns to generate targeted suggestions
        issue_categories = {}
        for issue in issues:
            category = issue.issue_type.value
            if category not in issue_categories:
                issue_categories[category] = []
            issue_categories[category].append(issue)
        
        # Generate suggestions based on issue patterns
        for category, category_issues in issue_categories.items():
            if len(category_issues) >= 3:  # Multiple issues in same category
                if category == ContentIssueType.TECHNICAL_ACCURACY.value:
                    suggestions.append({
                        "type": "comprehensive_review",
                        "priority": "high",
                        "title": "Техническая точность требует улучшения",
                        "description": "Множественные проблемы с техническими параметрами",
                        "action": "Провести комплексный пересмотр всех технических параметров с привлечением экспертов",
                        "affected_sections": list(set([issue.section for issue in category_issues]))
                    })
                
                elif category == ContentIssueType.SAFETY_COMPLIANCE.value:
                    suggestions.append({
                        "type": "safety_integration",
                        "priority": "critical",
                        "title": "Требуется усиление мер безопасности",
                        "description": "Выявлены множественные пробелы в обеспечении безопасности",
                        "action": "Провести комплексную оценку рисков и интегрировать меры безопасности во все процедуры",
                        "affected_sections": list(set([issue.section for issue in category_issues]))
                    })
        
        # Generate content-specific enhancement suggestions
        content_suggestions = self._analyze_content_for_enhancements(content, reference_docs)
        suggestions.extend(content_suggestions)
        
        return suggestions
    
    def _analyze_content_for_enhancements(self, content: str, reference_docs: List[str] = None) -> List[Dict[str, Any]]:
        """Analyze content to identify enhancement opportunities"""
        
        suggestions = []
        
        # Check content length and depth
        if len(content) < 2000:
            suggestions.append({
                "type": "content_expansion",
                "priority": "medium",
                "title": "Документ требует расширения",
                "description": "Содержание недостаточно детализировано для производственного использования",
                "action": "Добавить детальные процедуры, спецификации и примеры",
                "affected_sections": ["Все разделы"]
            })
        
        # Check for generic vs specific content
        generic_phrases = [
            "проверить готовность", "убедиться в работоспособности", 
            "выполнить необходимые действия", "при необходимости"
        ]
        
        generic_count = sum(1 for phrase in generic_phrases if phrase in content.lower())
        
        if generic_count > 3:
            suggestions.append({
                "type": "specificity_improvement", 
                "priority": "high",
                "title": "Замена общих формулировок конкретными инструкциями",
                "description": f"Найдено {generic_count} общих формулировок, требующих конкретизации",
                "action": "Заменить общие фразы конкретными, измеримыми инструкциями",
                "affected_sections": ["Процедуры"]
            })
        
        # Check for missing tables and structured data
        table_count = content.count("|")  # Simple markdown table detection
        param_count = len(re.findall(r'\d+(?:\.\d+)?\s*[°℃бармлмин]', content))
        
        if param_count > 5 and table_count < 10:
            suggestions.append({
                "type": "structure_improvement",
                "priority": "medium", 
                "title": "Структурирование технических данных",
                "description": "Технические параметры лучше представить в табличном виде",
                "action": "Создать таблицы для технических параметров, спецификаций и критериев",
                "affected_sections": ["Технические характеристики", "Параметры"]
            })
        
        # Reference document integration suggestions
        if reference_docs and len(reference_docs) > 0:
            suggestions.append({
                "type": "reference_integration",
                "priority": "high",
                "title": "Интеграция справочных материалов",
                "description": "Доступны справочные документы для улучшения содержания",
                "action": "Интегрировать конкретные данные из справочных материалов",
                "affected_sections": ["Технические характеристики", "Процедуры"]
            })
        
        return suggestions
    
    def generate_validation_report(self, validation_result: ContentValidationResult) -> str:
        """Generate comprehensive validation report"""
        
        report = []
        report.append("# ОТЧЕТ О ВАЛИДАЦИИ СОДЕРЖАНИЯ СОП\n")
        
        # Overall assessment
        report.append("## Общая оценка\n")
        report.append(f"**Общий балл:** {validation_result.overall_score:.1f}/100")
        report.append(f"**Достигнутый уровень валидации:** {validation_result.validation_level.value}")
        report.append("")
        
        # Category scores
        report.append("## Оценка по категориям\n")
        report.append(f"- **Техническая точность:** {validation_result.technical_accuracy_score:.1f}/100")
        report.append(f"- **Полнота содержания:** {validation_result.completeness_score:.1f}/100") 
        report.append(f"- **Соответствие стандартам:** {validation_result.regulatory_score:.1f}/100")
        report.append(f"- **Безопасность:** {validation_result.safety_score:.1f}/100")
        report.append("")
        
        # Issues summary
        if validation_result.issues:
            report.append("## Выявленные проблемы\n")
            
            # Group issues by severity
            critical_issues = [i for i in validation_result.issues if i.severity == "critical"]
            major_issues = [i for i in validation_result.issues if i.severity == "major"]
            minor_issues = [i for i in validation_result.issues if i.severity == "minor"]
            
            if critical_issues:
                report.append("### ❌ Критические проблемы\n")
                for issue in critical_issues:
                    report.append(f"**{issue.section}:** {issue.description}")
                    report.append(f"*Рекомендация:* {issue.suggested_improvement}")
                    report.append("")
            
            if major_issues:
                report.append("### ⚠️ Значительные проблемы\n")
                for issue in major_issues[:10]:  # Limit to first 10
                    report.append(f"**{issue.section}:** {issue.description}")
                    report.append(f"*Рекомендация:* {issue.suggested_improvement}")
                    report.append("")
            
            if minor_issues:
                report.append(f"### ℹ️ Незначительные замечания ({len(minor_issues)} шт.)\n")
                for issue in minor_issues[:5]:  # Show first 5
                    report.append(f"- {issue.description}")
                if len(minor_issues) > 5:
                    report.append(f"... и еще {len(minor_issues) - 5} замечаний")
                report.append("")
        
        # Enhancement suggestions
        if validation_result.enhancement_suggestions:
            report.append("## Предложения по улучшению\n")
            
            for suggestion in validation_result.enhancement_suggestions:
                priority_emoji = {"critical": "🔥", "high": "⚡", "medium": "📋", "low": "💡"}
                emoji = priority_emoji.get(suggestion["priority"], "📋")
                
                report.append(f"### {emoji} {suggestion['title']}")
                report.append(f"**Приоритет:** {suggestion['priority']}")
                report.append(f"**Описание:** {suggestion['description']}")
                report.append(f"**Рекомендуемые действия:** {suggestion['action']}")
                
                if suggestion.get("affected_sections"):
                    report.append(f"**Затронутые разделы:** {', '.join(suggestion['affected_sections'])}")
                report.append("")
        
        # Missing sections
        if validation_result.missing_sections:
            report.append("## Отсутствующие обязательные разделы\n")
            for section in validation_result.missing_sections:
                report.append(f"- {section}")
            report.append("")
        
        # Recommendations for next steps
        report.append("## Рекомендации по дальнейшим действиям\n")
        
        if validation_result.overall_score < 70:
            report.append("🚨 **Требуется значительная переработка документа**")
            report.append("- Устраните все критические проблемы")
            report.append("- Добавьте отсутствующие обязательные разделы")
            report.append("- Проведите техническую экспертизу содержания")
        elif validation_result.overall_score < 85:
            report.append("⚠️ **Требуется доработка перед использованием**")
            report.append("- Устраните критические проблемы")
            report.append("- Рассмотрите предложения по улучшению")
            report.append("- Проведите дополнительную проверку технических параметров")
        else:
            report.append("✅ **Документ близок к готовности к использованию**")
            report.append("- Устраните оставшиеся критические проблемы")
            report.append("- Рассмотрите предложения по улучшению качества")
            report.append("- Проведите финальную проверку перед утверждением")
        
        report.append("")
        
        return "\n".join(report)
    
    # Helper methods
    def _get_line_number(self, content: str, position: int) -> int:
        """Get line number for a given position in content"""
        return content[:position].count('\n') + 1
    
    def _extract_parameters_from_content(self, content: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract technical parameters from content"""
        parameters = {}
        
        # Temperature parameters
        temp_matches = re.findall(r'температур[аеы]?\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*[°℃]?([CF]?)', content, re.IGNORECASE)
        if temp_matches:
            parameters["температура"] = [{"value": match[0], "unit": "°C"} for match in temp_matches]
        
        # Pressure parameters  
        pressure_matches = re.findall(r'давлени[ея]?\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(бар|bar|кПа|МПа|атм)', content, re.IGNORECASE)
        if pressure_matches:
            parameters["давление"] = [{"value": match[0], "unit": match[1]} for match in pressure_matches]
        
        return parameters
    
    def _parameters_match(self, content_values: List[Dict], ref_values: List[Dict]) -> bool:
        """Check if content parameters match reference values"""
        # Simplified matching logic - can be enhanced
        if not content_values or not ref_values:
            return True
        
        # Check if at least one content value matches reference range
        for content_val in content_values:
            try:
                val = float(content_val["value"])
                for ref_val in ref_values:
                    try:
                        ref_num = float(ref_val["value"])
                        # Allow 20% tolerance
                        if 0.8 * ref_num <= val <= 1.2 * ref_num:
                            return True
                    except ValueError:
                        continue
            except ValueError:
                continue
        
        return False
    
    def _determine_validation_level(self, overall_score: float, issues: List[ValidationIssue]) -> ValidationLevel:
        """Determine achieved validation level"""
        
        critical_issues = [i for i in issues if i.severity == "critical"]
        
        if overall_score >= 95 and len(critical_issues) == 0:
            return ValidationLevel.PRODUCTION_READY
        elif overall_score >= 80 and len(critical_issues) <= 1:
            return ValidationLevel.PROFESSIONAL
        else:
            return ValidationLevel.BASIC