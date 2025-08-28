from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import re


@dataclass
class SectionRequirement:
    """Requirements for a mandatory SOP section"""
    title: str
    required_keywords: List[str]
    min_length: int = 100
    description: str = ""


class SOPSectionValidator:
    """Validates that SOP documents contain all mandatory sections with proper content"""
    
    MANDATORY_SECTIONS = [
        SectionRequirement(
            title="Цель и область применения",
            required_keywords=["цель", "область применения", "ограничения", "исключения"],
            min_length=150,
            description="Must define purpose, scope, limitations and exclusions"
        ),
        SectionRequirement(
            title="Ответственность и обучение",
            required_keywords=["ответственный", "квалификация", "обучение", "сертификация"],
            min_length=100,
            description="Must define roles, responsibilities and training requirements"
        ),
        SectionRequirement(
            title="Анализ рисков и безопасность",
            required_keywords=["риск", "опасность", "СИЗ", "безопасность", "предупреждение"],
            min_length=200,
            description="Must include detailed hazard analysis and safety measures"
        ),
        SectionRequirement(
            title="Оборудование и материалы",
            required_keywords=["оборудование", "материалы", "спецификация", "модель"],
            min_length=150,
            description="Must list equipment with specifications and part numbers"
        ),
        SectionRequirement(
            title="Пошаговые процедуры",
            required_keywords=["шаг", "процедура", "параметр", "диапазон", "критерий"],
            min_length=300,
            description="Must contain detailed steps with parameters and success criteria"
        ),
        SectionRequirement(
            title="Контроль качества",
            required_keywords=["качество", "контроль", "критерий", "приемка", "валидация"],
            min_length=120,
            description="Must define quality control measures and acceptance criteria"
        ),
        SectionRequirement(
            title="Документооборот и записи",
            required_keywords=["документ", "запись", "регистрация", "архив"],
            min_length=80,
            description="Must specify documentation and record keeping requirements"
        ),
        SectionRequirement(
            title="Нормативные ссылки",
            required_keywords=["ГОСТ", "стандарт", "норматив", "ссылка", "ISO"],
            min_length=50,
            description="Must reference applicable standards and regulations"
        ),
        SectionRequirement(
            title="Устранение неисправностей",
            required_keywords=["неисправность", "проблема", "решение", "диагностика", "устранение"],
            min_length=100,
            description="Must include troubleshooting procedures"
        )
    ]
    
    TECHNICAL_DETAIL_PATTERNS = [
        r'\d+\s*[°C°F]',  # Temperature values
        r'\d+\s*[бар|Па|атм|мм.рт.ст]',  # Pressure values  
        r'\d+\s*[сек|мин|час]',  # Time values
        r'\d+\s*[мл|л|г|кг]',  # Volume/mass values
        r'\d+[-±]\d+',  # Ranges
        r'≤|≥|<|>|\d+\s*%',  # Criteria and percentages
    ]
    
    SAFETY_INTEGRATION_PATTERNS = [
        r'\*\*ВНИМАНИЕ\*\*|\*\*ПРЕДУПРЕЖДЕНИЕ\*\*',  # Safety warnings
        r'СИЗ:|защит\w+\s+очки|респиратор|перчатк',  # PPE requirements
        r'ЛОТО|блокировк|отключен',  # Lockout/tagout
        r'аварийн\w+\s+процедур|экстренн\w+\s+действи',  # Emergency procedures
    ]

    def __init__(self):
        self.validation_results = {}

    def validate_section_presence(self, sop_content: str) -> Tuple[List[str], List[str]]:
        """
        Check if all mandatory sections are present in SOP content
        Returns: (found_sections, missing_sections)
        """
        found_sections = []
        missing_sections = []
        
        content_lower = sop_content.lower()
        
        for section in self.MANDATORY_SECTIONS:
            # Look for section headers (# ## ### or **bold**)
            section_patterns = [
                rf'#+\s*{re.escape(section.title.lower())}',
                rf'\*\*{re.escape(section.title.lower())}\*\*',
                rf'^{re.escape(section.title.lower())}$',
                rf'^\d+\.\s*{re.escape(section.title.lower())}'
            ]
            
            section_found = any(re.search(pattern, content_lower, re.MULTILINE | re.IGNORECASE) 
                             for pattern in section_patterns)
            
            if section_found:
                found_sections.append(section.title)
            else:
                missing_sections.append(section.title)
                
        return found_sections, missing_sections

    def validate_technical_depth(self, sop_content: str) -> Dict[str, Any]:
        """Validate that SOP contains sufficient technical details"""
        technical_matches = []
        
        for pattern in self.TECHNICAL_DETAIL_PATTERNS:
            matches = re.findall(pattern, sop_content, re.IGNORECASE)
            technical_matches.extend(matches)
            
        return {
            "technical_parameters_found": len(technical_matches),
            "has_sufficient_detail": len(technical_matches) >= 5,
            "examples": technical_matches[:10]  # First 10 examples
        }

    def validate_safety_integration(self, sop_content: str) -> Dict[str, Any]:
        """Validate that safety considerations are properly integrated"""
        safety_matches = []
        
        for pattern in self.SAFETY_INTEGRATION_PATTERNS:
            matches = re.findall(pattern, sop_content, re.IGNORECASE)
            safety_matches.extend(matches)
            
        return {
            "safety_elements_found": len(safety_matches),
            "has_integrated_safety": len(safety_matches) >= 3,
            "examples": safety_matches[:5]
        }

    def validate_section_content_quality(self, sop_content: str) -> Dict[str, Dict[str, Any]]:
        """Validate the quality and completeness of individual sections"""
        section_quality = {}
        
        for section in self.MANDATORY_SECTIONS:
            # Extract section content (rough approximation)
            section_pattern = rf'#+\s*{re.escape(section.title)}.*?(?=#+|\Z)'
            section_match = re.search(section_pattern, sop_content, 
                                    re.IGNORECASE | re.DOTALL)
            
            if section_match:
                section_content = section_match.group(0)
                
                # Check length
                meets_length = len(section_content) >= section.min_length
                
                # Check for required keywords
                keyword_matches = [kw for kw in section.required_keywords 
                                 if kw.lower() in section_content.lower()]
                has_keywords = len(keyword_matches) >= len(section.required_keywords) // 2
                
                section_quality[section.title] = {
                    "found": True,
                    "length": len(section_content),
                    "meets_min_length": meets_length,
                    "required_keywords_found": keyword_matches,
                    "has_sufficient_keywords": has_keywords,
                    "quality_score": (int(meets_length) + int(has_keywords)) / 2
                }
            else:
                section_quality[section.title] = {
                    "found": False,
                    "quality_score": 0
                }
                
        return section_quality

    def comprehensive_validation(self, sop_content: str) -> Dict[str, Any]:
        """Perform comprehensive validation of SOP document"""
        
        # Section presence check
        found_sections, missing_sections = self.validate_section_presence(sop_content)
        
        # Technical depth validation
        technical_validation = self.validate_technical_depth(sop_content)
        
        # Safety integration validation
        safety_validation = self.validate_safety_integration(sop_content)
        
        # Individual section quality
        section_quality = self.validate_section_content_quality(sop_content)
        
        # Overall assessment
        section_completeness_score = len(found_sections) / len(self.MANDATORY_SECTIONS)
        
        overall_quality_score = (
            section_completeness_score * 0.4 +
            (technical_validation["has_sufficient_detail"]) * 0.3 +
            (safety_validation["has_integrated_safety"]) * 0.3
        )
        
        is_production_ready = (
            len(missing_sections) == 0 and
            technical_validation["has_sufficient_detail"] and
            safety_validation["has_integrated_safety"] and
            overall_quality_score >= 0.8
        )
        
        return {
            "overall_assessment": {
                "is_production_ready": is_production_ready,
                "quality_score": overall_quality_score,
                "completeness_percentage": section_completeness_score * 100
            },
            "section_analysis": {
                "found_sections": found_sections,
                "missing_sections": missing_sections,
                "section_quality": section_quality
            },
            "technical_analysis": technical_validation,
            "safety_analysis": safety_validation,
            "recommendations": self._generate_recommendations(
                missing_sections, technical_validation, safety_validation
            )
        }

    def _generate_recommendations(self, missing_sections: List[str], 
                                technical_validation: Dict, 
                                safety_validation: Dict) -> List[str]:
        """Generate specific recommendations for improvement"""
        recommendations = []
        
        if missing_sections:
            recommendations.append(
                f"Добавить обязательные разделы: {', '.join(missing_sections)}"
            )
            
        if not technical_validation["has_sufficient_detail"]:
            recommendations.append(
                "Увеличить техническую детализацию: добавить конкретные параметры, "
                "диапазоны значений, настройки оборудования и критерии успеха"
            )
            
        if not safety_validation["has_integrated_safety"]:
            recommendations.append(
                "Усилить интеграцию безопасности: добавить предупреждения в процедурные шаги, "
                "детализировать требования к СИЗ, включить аварийные процедуры"
            )
            
        return recommendations


def create_mandatory_sections_template() -> List[Dict[str, Any]]:
    """Generate template with all mandatory sections"""
    sections = []
    
    for i, section_req in enumerate(SOPSectionValidator.MANDATORY_SECTIONS, 1):
        sections.append({
            "title": section_req.title,
            "mode": "ai",
            "prompt": f"Создай детальный раздел '{section_req.title}' с учетом следующих требований: {section_req.description}. Включи конкретные технические детали и интегрированные меры безопасности.",
            "content": "",
            "order": i
        })
    
    return sections