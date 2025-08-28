from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import re
import json
from pathlib import Path


class SOPReadinessLevel(Enum):
    PRODUCTION_READY = "PRODUCTION READY"
    REVIEW_REQUIRED = "REVIEW REQUIRED"  
    MAJOR_REVISION_NEEDED = "MAJOR REVISION NEEDED"


class IssueLevel(Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    SUGGESTION = "SUGGESTION"


@dataclass
class QualityIssue:
    level: IssueLevel
    section: str
    description: str
    improvement_suggestion: str
    line_reference: Optional[int] = None
    resolved: bool = False


@dataclass
class QualityScore:
    category: str
    score: int  # 0-100
    max_score: int = 100
    issues: List[QualityIssue] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []

    @property
    def percentage(self) -> float:
        return (self.score / self.max_score) * 100


@dataclass
class SOPReadinessAssessment:
    overall_status: SOPReadinessLevel
    overall_score: int
    technical_completeness: QualityScore
    safety_coverage: QualityScore
    operational_clarity: QualityScore
    regulatory_compliance: QualityScore
    professional_standards: QualityScore
    
    @property
    def critical_issues(self) -> List[QualityIssue]:
        issues = []
        for score in [self.technical_completeness, self.safety_coverage, 
                     self.operational_clarity, self.regulatory_compliance, 
                     self.professional_standards]:
            issues.extend([issue for issue in score.issues if issue.level == IssueLevel.CRITICAL])
        return issues
    
    @property
    def warnings(self) -> List[QualityIssue]:
        issues = []
        for score in [self.technical_completeness, self.safety_coverage,
                     self.operational_clarity, self.regulatory_compliance,
                     self.professional_standards]:
            issues.extend([issue for issue in score.issues if issue.level == IssueLevel.WARNING])
        return issues
    
    @property
    def suggestions(self) -> List[QualityIssue]:
        issues = []
        for score in [self.technical_completeness, self.safety_coverage,
                     self.operational_clarity, self.regulatory_compliance,
                     self.professional_standards]:
            issues.extend([issue for issue in score.issues if issue.level == IssueLevel.SUGGESTION])
        return issues


class ProfessionalSOPAssessor:
    """Professional-grade SOP quality assessment system for production readiness"""
    
    def __init__(self):
        self.technical_patterns = self._load_technical_patterns()
        self.safety_patterns = self._load_safety_patterns()
        self.regulatory_patterns = self._load_regulatory_patterns()
        
    def _load_technical_patterns(self) -> Dict[str, List[str]]:
        """Load technical validation patterns"""
        return {
            'specific_parameters': [
                r'\d+\.?\d*\s*[°℃][CF]?\b',  # Temperature with units
                r'\d+\.?\d*\s*(?:bar|Bar|кПа|МПа|атм|psi|mmHg)\b',  # Pressure 
                r'\d+\.?\d*\s*(?:мин|min|сек|sec|час|hr|h)\b',  # Time
                r'\d+\.?\d*\s*(?:мл|ml|л|L|г|g|кг|kg|мг|mg)\b',  # Volume/mass
                r'\d+\.?\d*\s*(?:об/мин|rpm|Гц|Hz)\b',  # Speed/frequency
                r'\d+\.?\d*\s*[±]\s*\d+\.?\d*',  # Tolerance ranges
                r'(?:от|from)\s+\d+\.?\d*\s+(?:до|to)\s+\d+\.?\d*',  # Ranges
            ],
            'equipment_specifications': [
                r'модель[:\s]+[A-Za-z0-9-]+',  # Model numbers
                r'серийный\s+номер[:\s]+[A-Za-z0-9-]+',  # Serial numbers
                r'версия\s+ПО[:\s]+[\d.]+',  # Software versions
                r'артикул[:\s]+[A-Za-z0-9-]+',  # Part numbers
                r'каталожный\s+номер[:\s]+[A-Za-z0-9-]+',  # Catalog numbers
            ],
            'calibration_procedures': [
                r'калибровка\s+каждые?\s+\d+\s*(?:дн|день|мес|месяц|год)',  # Calibration frequency
                r'стандартный\s+образец|эталон',  # Reference standards
                r'сертификат\s+калибровки',  # Calibration certificates
                r'допустимая\s+погрешность[:\s]*[±]?\d+\.?\d*%?',  # Accuracy specs
            ],
            'maintenance_schedules': [
                r'техническое\s+обслуживание\s+каждые?\s+\d+',  # Maintenance frequency
                r'замена\s+[\w\s]+каждые?\s+\d+',  # Replacement schedules
                r'профилактика\s+каждые?\s+\d+',  # Preventive maintenance
            ]
        }
    
    def _load_safety_patterns(self) -> Dict[str, List[str]]:
        """Load safety validation patterns"""
        return {
            'hazard_identification': [
                r'опасность[:\s]*(?:взрыв|пожар|токсич|корроз|радиац|механич)',
                r'риск[:\s]*(?:травм|ожог|отравл|поражен)',
                r'вредные?\s+факторы?[:\s]*',
                r'канцероген|мутаген|токсич|коррозионн|взрывоопасн',
            ],
            'ppe_specifications': [
                r'СИЗ[:\s]*(?:очки|перчатки|респиратор|халат|обувь)',
                r'защитные?\s+очки\s+класс[ао]?\s*\d+',
                r'перчатки\s+(?:нитрил|латекс|винил|резин)',
                r'респиратор\s+класс[ао]?\s*[A-Z]\d+',
                r'защитная\s+одежда\s+тип[ао]?\s*\d+[А-Я]?',
            ],
            'emergency_procedures': [
                r'при\s+аварии[:\s]*(?:немедленно|срочно|вызвать|эвакуир)',
                r'экстренн\w+\s+(?:действия|меры|процедуры)',
                r'первая\s+помощь[:\s]*',
                r'телефон\s+(?:спасательн|аварийн|службы?)\s*[:\d\s-()]+',
                r'душ\s+безопасности|промывка\s+глаз',
            ],
            'regulatory_references': [
                r'ГОСТ\s+[\d.-]+(?:-\d{2,4})?',
                r'СанПиН\s+[\d.]+',
                r'ТР\s+ТС\s+[\d/]+',
                r'ISO\s+\d+(?:[:-]\d+)?',
                r'OSHA\s+[\d.]+[A-Za-z]?',
                r'EPA\s+\d+\s*CFR\s+[\d.]+',
            ]
        }
    
    def _load_regulatory_patterns(self) -> Dict[str, List[str]]:
        """Load regulatory compliance patterns"""
        return {
            'documentation_requirements': [
                r'запись\s+в\s+журнал[еа]?',
                r'протокол\s+(?:испытан|калибров|провер)',
                r'сертификат\s+(?:соответств|калибров|анализа)',
                r'паспорт\s+безопасности',
                r'регистрация\s+в\s+(?:базе|системе)',
            ],
            'traceability': [
                r'прослеживаемость\s+до\s+(?:эталон|стандарт)',
                r'цепь\s+прослеживаемости',
                r'метрологическая\s+прослеживаемость',
                r'ссылка\s+на\s+стандарт',
            ],
            'quality_control': [
                r'контроль\s+качества\s+каждые?\s+\d+',
                r'внутренний\s+контроль\s+качества',
                r'межлабораторные?\s+сравнения?',
                r'контрольные?\s+карты?',
                r'статистический\s+контроль',
            ]
        }

    def assess_technical_completeness(self, sop_content: str) -> QualityScore:
        """Assess technical completeness (0-100)"""
        issues = []
        score = 100
        
        # Check for specific parameters (40 points)
        param_matches = 0
        for pattern_group in self.technical_patterns['specific_parameters']:
            matches = re.findall(pattern_group, sop_content, re.IGNORECASE)
            param_matches += len(matches)
        
        if param_matches < 5:
            deduction = min(40, (5 - param_matches) * 8)
            score -= deduction
            issues.append(QualityIssue(
                level=IssueLevel.CRITICAL,
                section="Технические параметры",
                description=f"Недостаточно конкретных технических параметров (найдено {param_matches}, требуется минимум 5)",
                improvement_suggestion="Добавьте конкретные значения температуры, давления, времени, объемов с единицами измерения и допусками"
            ))
        
        # Check for equipment specifications (25 points)
        spec_matches = 0
        for pattern in self.technical_patterns['equipment_specifications']:
            matches = re.findall(pattern, sop_content, re.IGNORECASE)
            spec_matches += len(matches)
        
        if spec_matches < 3:
            deduction = min(25, (3 - spec_matches) * 8)
            score -= deduction
            issues.append(QualityIssue(
                level=IssueLevel.CRITICAL,
                section="Спецификации оборудования",
                description=f"Отсутствуют спецификации оборудования (найдено {spec_matches}, требуется минимум 3)",
                improvement_suggestion="Укажите модели оборудования, серийные номера, версии ПО, артикулы"
            ))
        
        # Check for calibration procedures (20 points)
        calib_matches = 0
        for pattern in self.technical_patterns['calibration_procedures']:
            matches = re.findall(pattern, sop_content, re.IGNORECASE)
            calib_matches += len(matches)
        
        if calib_matches == 0:
            score -= 20
            issues.append(QualityIssue(
                level=IssueLevel.CRITICAL,
                section="Калибровка",
                description="Отсутствуют процедуры калибровки и поверки",
                improvement_suggestion="Добавьте требования к калибровке, периодичность, стандартные образцы, допустимые погрешности"
            ))
        
        # Check for maintenance procedures (15 points)
        maint_matches = 0
        for pattern in self.technical_patterns['maintenance_schedules']:
            matches = re.findall(pattern, sop_content, re.IGNORECASE)
            maint_matches += len(matches)
        
        if maint_matches == 0:
            score -= 15
            issues.append(QualityIssue(
                level=IssueLevel.WARNING,
                section="Техническое обслуживание",
                description="Отсутствуют требования к техническому обслуживанию",
                improvement_suggestion="Добавьте график технического обслуживания, процедуры профилактики, замены расходных материалов"
            ))
        
        return QualityScore(
            category="Technical Completeness",
            score=max(0, score),
            issues=issues
        )
    
    def assess_safety_coverage(self, sop_content: str) -> QualityScore:
        """Assess safety coverage (0-100)"""
        issues = []
        score = 100
        
        # Check hazard identification (30 points)
        hazard_matches = 0
        for pattern in self.safety_patterns['hazard_identification']:
            matches = re.findall(pattern, sop_content, re.IGNORECASE)
            hazard_matches += len(matches)
        
        if hazard_matches < 3:
            deduction = min(30, (3 - hazard_matches) * 10)
            score -= deduction
            issues.append(QualityIssue(
                level=IssueLevel.CRITICAL,
                section="Анализ опасностей",
                description=f"Недостаточная идентификация опасностей (найдено {hazard_matches}, требуется минимум 3)",
                improvement_suggestion="Проведите детальный анализ химических, физических, биологических и эргономических рисков"
            ))
        
        # Check PPE specifications (25 points)
        ppe_matches = 0
        for pattern in self.safety_patterns['ppe_specifications']:
            matches = re.findall(pattern, sop_content, re.IGNORECASE)
            ppe_matches += len(matches)
        
        if ppe_matches < 2:
            deduction = min(25, (2 - ppe_matches) * 12)
            score -= deduction
            issues.append(QualityIssue(
                level=IssueLevel.CRITICAL,
                section="СИЗ",
                description=f"Недостаточно детализированы требования к СИЗ (найдено {ppe_matches}, требуется минимум 2)",
                improvement_suggestion="Укажите конкретные типы, классы и стандарты СИЗ для каждой операции"
            ))
        
        # Check emergency procedures (25 points)
        emergency_matches = 0
        for pattern in self.safety_patterns['emergency_procedures']:
            matches = re.findall(pattern, sop_content, re.IGNORECASE)
            emergency_matches += len(matches)
        
        if emergency_matches < 2:
            deduction = min(25, (2 - emergency_matches) * 12)
            score -= deduction
            issues.append(QualityIssue(
                level=IssueLevel.CRITICAL,
                section="Аварийные процедуры",
                description=f"Недостаточно аварийных процедур (найдено {emergency_matches}, требуется минимум 2)",
                improvement_suggestion="Добавьте детальные процедуры для каждого типа чрезвычайной ситуации, контактную информацию"
            ))
        
        # Check regulatory references (20 points)
        reg_matches = 0
        for pattern in self.safety_patterns['regulatory_references']:
            matches = re.findall(pattern, sop_content, re.IGNORECASE)
            reg_matches += len(matches)
        
        if reg_matches == 0:
            score -= 20
            issues.append(QualityIssue(
                level=IssueLevel.WARNING,
                section="Нормативные ссылки",
                description="Отсутствуют ссылки на стандарты безопасности",
                improvement_suggestion="Добавьте ссылки на ГОСТ, СанПиН, ISO 45001, OSHA и другие применимые стандарты"
            ))
        
        return QualityScore(
            category="Safety Coverage",
            score=max(0, score),
            issues=issues
        )
    
    def assess_operational_clarity(self, sop_content: str) -> QualityScore:
        """Assess operational clarity (0-100)"""
        issues = []
        score = 100
        
        # Check for step-by-step structure (30 points)
        step_patterns = [
            r'^\d+\.\s+',  # Numbered steps
            r'Шаг\s+\d+[:\.]',  # Step indicators
            r'Этап\s+\d+[:\.]',  # Stage indicators
        ]
        
        step_matches = 0
        for pattern in step_patterns:
            matches = re.findall(pattern, sop_content, re.MULTILINE | re.IGNORECASE)
            step_matches += len(matches)
        
        if step_matches < 5:
            deduction = min(30, (5 - step_matches) * 6)
            score -= deduction
            issues.append(QualityIssue(
                level=IssueLevel.CRITICAL,
                section="Структура процедур",
                description=f"Недостаточно пошаговых инструкций (найдено {step_matches}, требуется минимум 5)",
                improvement_suggestion="Структурируйте все процедуры в виде четких пронумерованных шагов"
            ))
        
        # Check for decision points (25 points)
        decision_patterns = [
            r'если\s+.*,\s*то',  # Conditional statements
            r'в\s+случае\s+если',  # If-case statements
            r'при\s+(?:превышении|отклонении|несоответствии)',  # Exception conditions
            r'критерий\s+(?:приемки|соответствия)',  # Acceptance criteria
        ]
        
        decision_matches = 0
        for pattern in decision_patterns:
            matches = re.findall(pattern, sop_content, re.IGNORECASE)
            decision_matches += len(matches)
        
        if decision_matches < 3:
            deduction = min(25, (3 - decision_matches) * 8)
            score -= deduction
            issues.append(QualityIssue(
                level=IssueLevel.WARNING,
                section="Точки принятия решений",
                description=f"Недостаточно точек принятия решений (найдено {decision_matches}, требуется минимум 3)",
                improvement_suggestion="Добавьте условные операции, критерии приемки, действия при отклонениях"
            ))
        
        # Check for troubleshooting (20 points)
        troubleshoot_patterns = [
            r'устранение\s+неисправност',
            r'диагностика\s+проблем',
            r'возможные?\s+причины?',
            r'способы?\s+решения',
            r'если\s+(?:ошибка|проблема|неисправность)',
        ]
        
        troubleshoot_matches = 0
        for pattern in troubleshoot_patterns:
            matches = re.findall(pattern, sop_content, re.IGNORECASE)
            troubleshoot_matches += len(matches)
        
        if troubleshoot_matches < 2:
            deduction = min(20, (2 - troubleshoot_matches) * 10)
            score -= deduction
            issues.append(QualityIssue(
                level=IssueLevel.WARNING,
                section="Устранение неисправностей",
                description=f"Недостаточно информации по устранению неисправностей (найдено {troubleshoot_matches}, требуется минимум 2)",
                improvement_suggestion="Добавьте раздел диагностики проблем с описанием симптомов, причин и способов решения"
            ))
        
        # Check for success criteria (25 points)
        success_patterns = [
            r'критерий\s+(?:успеха|выполнения)',
            r'признак\s+(?:правильного|успешного)',
            r'результат\s+(?:должен|считается)',
            r'приемлем\w+\s+(?:значения?|диапазон|результат)',
        ]
        
        success_matches = 0
        for pattern in success_patterns:
            matches = re.findall(pattern, sop_content, re.IGNORECASE)
            success_matches += len(matches)
        
        if success_matches < 2:
            deduction = min(25, (2 - success_matches) * 12)
            score -= deduction
            issues.append(QualityIssue(
                level=IssueLevel.CRITICAL,
                section="Критерии успеха",
                description=f"Недостаточно критериев успешного выполнения (найдено {success_matches}, требуется минимум 2)",
                improvement_suggestion="Определите четкие критерии успешного выполнения для каждого ключевого этапа"
            ))
        
        return QualityScore(
            category="Operational Clarity",
            score=max(0, score),
            issues=issues
        )
    
    def assess_regulatory_compliance(self, sop_content: str) -> QualityScore:
        """Assess regulatory compliance (0-100)"""
        issues = []
        score = 100
        
        # Check documentation requirements (40 points)
        doc_matches = 0
        for pattern in self.regulatory_patterns['documentation_requirements']:
            matches = re.findall(pattern, sop_content, re.IGNORECASE)
            doc_matches += len(matches)
        
        if doc_matches < 2:
            deduction = min(40, (2 - doc_matches) * 20)
            score -= deduction
            issues.append(QualityIssue(
                level=IssueLevel.CRITICAL,
                section="Документооборот",
                description=f"Недостаточные требования к документообороту (найдено {doc_matches}, требуется минимум 2)",
                improvement_suggestion="Определите требования к ведению записей, протоколов, сертификатов"
            ))
        
        # Check traceability requirements (30 points)
        trace_matches = 0
        for pattern in self.regulatory_patterns['traceability']:
            matches = re.findall(pattern, sop_content, re.IGNORECASE)
            trace_matches += len(matches)
        
        if trace_matches == 0:
            score -= 30
            issues.append(QualityIssue(
                level=IssueLevel.CRITICAL,
                section="Прослеживаемость",
                description="Отсутствуют требования к прослеживаемости",
                improvement_suggestion="Обеспечьте прослеживаемость до национальных и международных стандартов"
            ))
        
        # Check quality control integration (30 points)
        qc_matches = 0
        for pattern in self.regulatory_patterns['quality_control']:
            matches = re.findall(pattern, sop_content, re.IGNORECASE)
            qc_matches += len(matches)
        
        if qc_matches == 0:
            score -= 30
            issues.append(QualityIssue(
                level=IssueLevel.WARNING,
                section="Контроль качества",
                description="Недостаточная интеграция с системой контроля качества",
                improvement_suggestion="Включите процедуры внутреннего контроля качества, статистического анализа"
            ))
        
        return QualityScore(
            category="Regulatory Compliance",
            score=max(0, score),
            issues=issues
        )
    
    def assess_professional_standards(self, sop_content: str) -> QualityScore:
        """Assess professional standards (0-100)"""
        issues = []
        score = 100
        
        # Check document structure (30 points)
        required_sections = [
            r'#.*(?:цель|назначение|область\s+применения)',
            r'#.*(?:ответственность|персонал)',
            r'#.*(?:безопасность|риск|опасность)',
            r'#.*(?:оборудование|материалы|средства)',
            r'#.*(?:процедура|методика|порядок)',
            r'#.*(?:контроль|качество)',
            r'#.*(?:документ|запись)',
            r'#.*(?:ссылки|стандарт|норматив)',
        ]
        
        section_matches = 0
        for pattern in required_sections:
            if re.search(pattern, sop_content, re.IGNORECASE):
                section_matches += 1
        
        if section_matches < 6:
            deduction = min(30, (6 - section_matches) * 5)
            score -= deduction
            issues.append(QualityIssue(
                level=IssueLevel.CRITICAL,
                section="Структура документа",
                description=f"Отсутствуют обязательные разделы (найдено {section_matches} из 8 требуемых)",
                improvement_suggestion="Включите все стандартные разделы СОП согласно требованиям ISO 17025"
            ))
        
        # Check terminology consistency (25 points)
        inconsistent_terms = self._check_terminology_consistency(sop_content)
        if len(inconsistent_terms) > 3:
            score -= 25
            issues.append(QualityIssue(
                level=IssueLevel.WARNING,
                section="Терминология",
                description=f"Обнаружены несогласованные термины: {', '.join(inconsistent_terms[:5])}",
                improvement_suggestion="Обеспечьте единообразное использование технических терминов"
            ))
        
        # Check formatting consistency (25 points)
        formatting_issues = self._check_formatting_consistency(sop_content)
        if len(formatting_issues) > 2:
            deduction = min(25, len(formatting_issues) * 5)
            score -= deduction
            issues.append(QualityIssue(
                level=IssueLevel.SUGGESTION,
                section="Форматирование",
                description=f"Обнаружены проблемы форматирования: {len(formatting_issues)} случаев",
                improvement_suggestion="Обеспечьте единообразное форматирование заголовков, списков, таблиц"
            ))
        
        # Check completeness indicators (20 points)
        if len(sop_content) < 2000:
            score -= 20
            issues.append(QualityIssue(
                level=IssueLevel.CRITICAL,
                section="Полнота документа",
                description="Документ слишком краток для производственного использования",
                improvement_suggestion="Расширьте содержание до минимум 2000 символов с детальными процедурами"
            ))
        
        return QualityScore(
            category="Professional Standards",
            score=max(0, score),
            issues=issues
        )
    
    def _check_terminology_consistency(self, content: str) -> List[str]:
        """Check for inconsistent terminology usage"""
        inconsistent = []
        
        # Common inconsistency patterns
        patterns = {
            'temperature': [r'температур[аы]', r'темп\.', r'T='],
            'pressure': [r'давлен[иея]', r'P=', r'пресс'],
            'calibration': [r'калибровк[аи]', r'калибр\.', r'поверк[аи]'],
        }
        
        for term, pattern_list in patterns.items():
            found_variants = []
            for pattern in pattern_list:
                if re.search(pattern, content, re.IGNORECASE):
                    found_variants.append(pattern)
            if len(found_variants) > 1:
                inconsistent.append(term)
        
        return inconsistent
    
    def _check_formatting_consistency(self, content: str) -> List[str]:
        """Check for formatting inconsistencies"""
        issues = []
        
        # Check header consistency
        headers = re.findall(r'^#+\s+.*$', content, re.MULTILINE)
        if len(set(h[0] for h in headers)) > 2:  # More than 2 different header levels
            issues.append("inconsistent_headers")
        
        # Check list formatting
        list_bullets = re.findall(r'^[\s]*[-*•]\s+', content, re.MULTILINE)
        numbered_lists = re.findall(r'^[\s]*\d+[\.)]\s+', content, re.MULTILINE)
        if len(list_bullets) > 0 and len(numbered_lists) > 0:
            issues.append("mixed_list_styles")
        
        return issues

    def perform_comprehensive_assessment(self, sop_content: str) -> SOPReadinessAssessment:
        """Perform comprehensive SOP readiness assessment"""
        
        # Assess all categories
        technical = self.assess_technical_completeness(sop_content)
        safety = self.assess_safety_coverage(sop_content)
        operational = self.assess_operational_clarity(sop_content)
        regulatory = self.assess_regulatory_compliance(sop_content)
        professional = self.assess_professional_standards(sop_content)
        
        # Calculate overall score
        scores = [technical.score, safety.score, operational.score, regulatory.score, professional.score]
        overall_score = int(sum(scores) / len(scores))
        
        # Determine readiness level
        min_score = min(scores)
        if overall_score >= 95 and min_score >= 90:
            status = SOPReadinessLevel.PRODUCTION_READY
        elif overall_score >= 85 and min_score >= 70:
            status = SOPReadinessLevel.REVIEW_REQUIRED
        else:
            status = SOPReadinessLevel.MAJOR_REVISION_NEEDED
        
        return SOPReadinessAssessment(
            overall_status=status,
            overall_score=overall_score,
            technical_completeness=technical,
            safety_coverage=safety,
            operational_clarity=operational,
            regulatory_compliance=regulatory,
            professional_standards=professional
        )

    def generate_dashboard_data(self, assessment: SOPReadinessAssessment) -> Dict[str, Any]:
        """Generate data for the readiness dashboard UI"""
        return {
            "overall_status": assessment.overall_status.value,
            "overall_score": assessment.overall_score,
            "categories": [
                {
                    "name": "Technical Completeness",
                    "score": assessment.technical_completeness.score,
                    "percentage": assessment.technical_completeness.percentage
                },
                {
                    "name": "Safety Coverage",
                    "score": assessment.safety_coverage.score,
                    "percentage": assessment.safety_coverage.percentage
                },
                {
                    "name": "Operational Clarity", 
                    "score": assessment.operational_clarity.score,
                    "percentage": assessment.operational_clarity.percentage
                },
                {
                    "name": "Regulatory Compliance",
                    "score": assessment.regulatory_compliance.score,
                    "percentage": assessment.regulatory_compliance.percentage
                },
                {
                    "name": "Professional Standards",
                    "score": assessment.professional_standards.score,
                    "percentage": assessment.professional_standards.percentage
                }
            ],
            "issue_summary": {
                "critical_count": len(assessment.critical_issues),
                "warning_count": len(assessment.warnings),
                "suggestion_count": len(assessment.suggestions)
            },
            "critical_issues": [
                {
                    "level": issue.level.value,
                    "section": issue.section,
                    "description": issue.description,
                    "improvement": issue.improvement_suggestion
                }
                for issue in assessment.critical_issues
            ],
            "warnings": [
                {
                    "level": issue.level.value,
                    "section": issue.section,
                    "description": issue.description,
                    "improvement": issue.improvement_suggestion
                }
                for issue in assessment.warnings
            ],
            "suggestions": [
                {
                    "level": issue.level.value,
                    "section": issue.section,
                    "description": issue.description,
                    "improvement": issue.improvement_suggestion
                }
                for issue in assessment.suggestions
            ]
        }