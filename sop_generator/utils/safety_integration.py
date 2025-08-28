from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re
import json


class HazardCategory(Enum):
    CHEMICAL = "chemical"
    PHYSICAL = "physical"
    BIOLOGICAL = "biological"
    RADIOLOGICAL = "radiological"
    ERGONOMIC = "ergonomic"
    ENVIRONMENTAL = "environmental"


class RiskLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PPEType(Enum):
    EYE_PROTECTION = "eye_protection"
    RESPIRATORY = "respiratory"
    HAND_PROTECTION = "hand_protection"
    BODY_PROTECTION = "body_protection"
    FOOT_PROTECTION = "foot_protection"
    HEARING_PROTECTION = "hearing_protection"


@dataclass
class HazardAnalysis:
    hazard_id: str
    category: HazardCategory
    description: str
    risk_level: RiskLevel
    probability: str  # Very Low, Low, Medium, High, Very High
    severity: str    # Negligible, Minor, Moderate, Major, Catastrophic
    risk_rating: int  # 1-25 (probability × severity matrix)
    regulatory_references: List[str]
    control_measures: List[str]


@dataclass
class PPERequirement:
    ppe_type: PPEType
    specification: str
    performance_standard: str
    usage_conditions: str
    replacement_criteria: str
    regulatory_standard: str


@dataclass
class EmergencyProcedure:
    scenario: str
    immediate_actions: List[str]
    notification_procedure: List[str]
    evacuation_procedure: Optional[str]
    cleanup_procedure: Optional[str]
    reporting_requirements: List[str]
    contact_information: Dict[str, str]


@dataclass
class RegulatoryRequirement:
    standard_id: str
    title: str
    applicable_sections: List[str]
    compliance_requirements: List[str]
    documentation_needed: List[str]
    audit_frequency: str


class ProfessionalSafetyIntegrator:
    """Professional safety integration system with comprehensive regulatory compliance"""
    
    def __init__(self):
        self.chemical_database = self._load_chemical_hazard_database()
        self.ppe_database = self._load_ppe_specifications()
        self.regulatory_database = self._load_regulatory_requirements()
        self.emergency_procedures = self._load_emergency_procedures()
    
    def _load_chemical_hazard_database(self) -> Dict[str, Dict[str, Any]]:
        """Load chemical hazard information database"""
        return {
            "acids": {
                "hazards": ["коррозия кожи", "серьезное повреждение глаз", "коррозия металлов"],
                "ppe_requirements": ["acid_resistant_gloves", "face_shield", "acid_resistant_apron"],
                "emergency_procedures": ["acid_spill", "acid_contact"],
                "regulatory_classes": ["H314", "H318"],
                "cas_examples": ["7647-01-0", "7664-93-9", "7697-37-2"]
            },
            "organic_solvents": {
                "hazards": ["легковоспламеняющиеся жидкости", "токсичность", "раздражение"],
                "ppe_requirements": ["chemical_resistant_gloves", "safety_glasses", "lab_coat"],
                "emergency_procedures": ["solvent_spill", "fire_emergency", "inhalation_exposure"],
                "regulatory_classes": ["H225", "H226", "H302", "H315"],
                "cas_examples": ["67-56-1", "64-17-5", "75-09-2"]
            },
            "bases": {
                "hazards": ["коррозия кожи", "серьезное повреждение глаз"],
                "ppe_requirements": ["alkali_resistant_gloves", "face_shield", "chemical_apron"],
                "emergency_procedures": ["base_spill", "alkali_contact"],
                "regulatory_classes": ["H314", "H318"],
                "cas_examples": ["1310-73-2", "1310-58-3"]
            },
            "oxidizers": {
                "hazards": ["может усилить пожар", "взрывоопасность при контакте"],
                "ppe_requirements": ["oxidizer_resistant_gloves", "face_shield", "flame_resistant_clothing"],
                "emergency_procedures": ["oxidizer_spill", "fire_emergency"],
                "regulatory_classes": ["H270", "H271", "H272"],
                "cas_examples": ["7722-84-1", "7681-52-9"]
            }
        }
    
    def _load_ppe_specifications(self) -> Dict[PPEType, List[Dict[str, Any]]]:
        """Load PPE specifications database"""
        return {
            PPEType.EYE_PROTECTION: [
                {
                    "type": "Защитные очки",
                    "standard": "ГОСТ 12.4.013-85",
                    "specifications": "Класс защиты 1, оптический класс 1",
                    "applications": ["химические брызги", "пыль", "УФ излучение"],
                    "replacement": "При появлении царапин или помутнения"
                },
                {
                    "type": "Защитный щиток для лица",
                    "standard": "EN 166:2001",
                    "specifications": "Полная защита лица, антизапотевающее покрытие",
                    "applications": ["кислоты", "щелочи", "горячие жидкости"],
                    "replacement": "При повреждении защитного экрана"
                }
            ],
            PPEType.HAND_PROTECTION: [
                {
                    "type": "Нитриловые перчатки",
                    "standard": "EN 374-1:2016",
                    "specifications": "Толщина 0.12-0.20 мм, AQL ≤ 1.5",
                    "applications": ["органические растворители", "нефтепродукты", "слабые кислоты"],
                    "replacement": "После каждого использования или при повреждении"
                },
                {
                    "type": "Неопреновые перчатки",
                    "standard": "EN 374-1:2016",
                    "specifications": "Химическая стойкость класса 4-6",
                    "applications": ["концентрированные кислоты", "щелочи", "окислители"],
                    "replacement": "После контакта с агрессивными веществами"
                }
            ],
            PPEType.RESPIRATORY: [
                {
                    "type": "Полумаска с фильтрами",
                    "standard": "EN 140:1998 + A1:2018",
                    "specifications": "Класс защиты FFP2 или выше",
                    "applications": ["пыль", "аэрозоли", "пары органических растворителей"],
                    "replacement": "Фильтры каждые 8 часов работы"
                },
                {
                    "type": "Полнолицевая маска",
                    "standard": "EN 136:1998",
                    "specifications": "Класс 2, совместимость с фильтрами A1B1E1K1",
                    "applications": ["токсичные пары", "кислотные газы", "аммиак"],
                    "replacement": "Фильтры согласно индикатору насыщения"
                }
            ]
        }
    
    def _load_regulatory_requirements(self) -> Dict[str, RegulatoryRequirement]:
        """Load regulatory requirements database"""
        return {
            "GOST_12_1_005": RegulatoryRequirement(
                standard_id="ГОСТ 12.1.005-88",
                title="Общие санитарно-гигиенические требования к воздуху рабочей зоны",
                applicable_sections=["4.1", "4.2", "5.1"],
                compliance_requirements=[
                    "Контроль ПДК вредных веществ",
                    "Обеспечение вентиляции рабочих мест",
                    "Регулярный контроль качества воздуха"
                ],
                documentation_needed=[
                    "Протоколы измерения концентраций",
                    "Карты аттестации рабочих мест",
                    "Журналы технического обслуживания вентиляции"
                ],
                audit_frequency="ежегодно"
            ),
            "ISO_45001": RegulatoryRequirement(
                standard_id="ISO 45001:2018",
                title="Системы менеджмента охраны здоровья и обеспечения безопасности труда",
                applicable_sections=["6.1", "7.2", "8.1", "8.2"],
                compliance_requirements=[
                    "Идентификация опасностей и оценка рисков",
                    "Обучение персонала",
                    "Планирование и контроль операционной деятельности",
                    "Подготовленность к аварийным ситуациям"
                ],
                documentation_needed=[
                    "Реестр опасностей и рисков",
                    "Программы обучения",
                    "Процедуры безопасной работы",
                    "Планы реагирования на чрезвычайные ситуации"
                ],
                audit_frequency="ежегодно"
            ),
            "OSHA_1910": RegulatoryRequirement(
                standard_id="29 CFR 1910",
                title="Occupational Safety and Health Standards",
                applicable_sections=["1910.95", "1910.132", "1910.1200"],
                compliance_requirements=[
                    "Программа защиты органов слуха",
                    "Обеспечение СИЗ",
                    "Информирование об опасности химических веществ"
                ],
                documentation_needed=[
                    "Аудиометрические данные",
                    "Учет выдачи СИЗ",
                    "Паспорта безопасности химических веществ"
                ],
                audit_frequency="ежегодно"
            )
        }
    
    def _load_emergency_procedures(self) -> Dict[str, EmergencyProcedure]:
        """Load emergency procedures database"""
        return {
            "chemical_spill": EmergencyProcedure(
                scenario="Разлив химических веществ",
                immediate_actions=[
                    "Немедленно покинуть зону разлива",
                    "Предупредить персонал в помещении",
                    "Изолировать источник разлива (если безопасно)",
                    "Надеть соответствующие СИЗ",
                    "Локализовать разлив сорбентом"
                ],
                notification_procedure=[
                    "Уведомить руководителя лаборатории",
                    "При крупных разливах - службу экологической безопасности",
                    "При необходимости - службу 112"
                ],
                cleanup_procedure="Нейтрализация согласно SDS вещества, утилизация как опасные отходы",
                reporting_requirements=[
                    "Заполнить уведомление о происшествии",
                    "Провести расследование причин",
                    "Внести корректирующие действия в план"
                ],
                contact_information={
                    "Руководитель лаборатории": "[указать телефон]",
                    "Служба безопасности": "[указать телефон]",
                    "Экстренные службы": "112"
                }
            ),
            "fire_emergency": EmergencyProcedure(
                scenario="Пожар или возгорание",
                immediate_actions=[
                    "Объявить пожарную тревогу",
                    "Отключить электропитание оборудования",
                    "При небольшом возгорании - использовать огнетушитель",
                    "Эвакуироваться из помещения",
                    "Закрыть двери при выходе"
                ],
                notification_procedure=[
                    "Вызвать пожарную службу (101)",
                    "Уведомить службу безопасности объекта",
                    "Встретить пожарную команду"
                ],
                evacuation_procedure="Эвакуация по планам эвакуации, сбор в назначенном месте",
                reporting_requirements=[
                    "Заполнить акт о пожаре",
                    "Провести расследование",
                    "Разработать меры предотвращения"
                ],
                contact_information={
                    "Пожарная служба": "101",
                    "Служба безопасности": "[указать телефон]",
                    "Руководитель": "[указать телефон]"
                }
            ),
            "injury_emergency": EmergencyProcedure(
                scenario="Несчастный случай с пострадавшим",
                immediate_actions=[
                    "Обеспечить безопасность места происшествия",
                    "Оказать первую медицинскую помощь",
                    "Не перемещать пострадавшего при подозрении на травму позвоночника",
                    "Вызвать медицинскую помощь",
                    "Сохранить обстановку места происшествия"
                ],
                notification_procedure=[
                    "Вызвать скорую помощь (103)",
                    "Немедленно уведомить руководителя",
                    "Уведомить службу охраны труда"
                ],
                reporting_requirements=[
                    "Составить акт о несчастном случае",
                    "Провести расследование в установленные сроки",
                    "Разработать мероприятия по предотвращению"
                ],
                contact_information={
                    "Скорая помощь": "103",
                    "Медпункт организации": "[указать телефон]",
                    "Служба охраны труда": "[указать телефон]"
                }
            )
        }
    
    def analyze_hazards(self, sop_content: str, equipment_type: str = None, chemicals: List[str] = None) -> List[HazardAnalysis]:
        """Perform comprehensive hazard analysis"""
        
        hazards = []
        
        # Chemical hazard analysis
        if chemicals:
            for chemical in chemicals:
                chemical_hazards = self._analyze_chemical_hazards(chemical, sop_content)
                hazards.extend(chemical_hazards)
        
        # Extract chemicals from content
        detected_chemicals = self._detect_chemicals_in_content(sop_content)
        for chemical in detected_chemicals:
            chemical_hazards = self._analyze_chemical_hazards(chemical, sop_content)
            hazards.extend(chemical_hazards)
        
        # Equipment-specific hazards
        if equipment_type:
            equipment_hazards = self._analyze_equipment_hazards(equipment_type, sop_content)
            hazards.extend(equipment_hazards)
        
        # Physical hazards from content analysis
        physical_hazards = self._analyze_physical_hazards(sop_content)
        hazards.extend(physical_hazards)
        
        # Environmental hazards
        environmental_hazards = self._analyze_environmental_hazards(sop_content)
        hazards.extend(environmental_hazards)
        
        return hazards
    
    def _analyze_chemical_hazards(self, chemical: str, content: str) -> List[HazardAnalysis]:
        """Analyze chemical-specific hazards"""
        
        hazards = []
        chemical_lower = chemical.lower()
        
        # Match against chemical database
        for chem_type, info in self.chemical_database.items():
            if any(keyword in chemical_lower for keyword in chem_type.split('_')):
                for hazard_desc in info["hazards"]:
                    hazard = HazardAnalysis(
                        hazard_id=f"CHEM_{len(hazards)+1:03d}",
                        category=HazardCategory.CHEMICAL,
                        description=f"{chemical}: {hazard_desc}",
                        risk_level=self._assess_risk_level(hazard_desc, content),
                        probability="Medium",
                        severity=self._assess_severity(hazard_desc),
                        risk_rating=self._calculate_risk_rating("Medium", self._assess_severity(hazard_desc)),
                        regulatory_references=info["regulatory_classes"],
                        control_measures=self._generate_control_measures(hazard_desc, chemical)
                    )
                    hazards.append(hazard)
        
        return hazards
    
    def _analyze_equipment_hazards(self, equipment_type: str, content: str) -> List[HazardAnalysis]:
        """Analyze equipment-specific hazards"""
        
        hazards = []
        
        # Common equipment hazards
        equipment_hazard_map = {
            "chromatography": [
                ("Высокое давление системы", "Physical", "Major", ["Разрыв фитингов", "Травмы от струи растворителя"]),
                ("Токсичные растворители", "Chemical", "Moderate", ["Ингаляционное воздействие", "Контакт с кожей"]),
                ("Пожароопасные растворители", "Chemical", "Major", ["Воспламенение", "Взрыв паров"])
            ],
            "spectroscopy": [
                ("УФ-излучение", "Physical", "Moderate", ["Повреждение глаз", "Ожоги кожи"]),
                ("Кварцевые компоненты", "Physical", "Minor", ["Порезы при разрушении", "Осколки"]),
                ("Высокая температура ламп", "Physical", "Moderate", ["Термические ожоги"])
            ],
            "analytical_balance": [
                ("Статическое электричество", "Physical", "Minor", ["Искрообразование", "Помехи измерениям"]),
                ("Химически агрессивные вещества", "Chemical", "Moderate", ["Коррозия механизма", "Отравление"])
            ]
        }
        
        eq_type_lower = equipment_type.lower()
        for eq_key, hazard_list in equipment_hazard_map.items():
            if eq_key in eq_type_lower:
                for hazard_name, category, severity, consequences in hazard_list:
                    hazard = HazardAnalysis(
                        hazard_id=f"EQ_{len(hazards)+1:03d}",
                        category=HazardCategory.PHYSICAL if category == "Physical" else HazardCategory.CHEMICAL,
                        description=f"{hazard_name} (оборудование: {equipment_type})",
                        risk_level=self._severity_to_risk_level(severity),
                        probability="Medium",
                        severity=severity,
                        risk_rating=self._calculate_risk_rating("Medium", severity),
                        regulatory_references=["ГОСТ 12.2.003-91", "ISO 12100:2010"],
                        control_measures=self._generate_equipment_controls(hazard_name, consequences)
                    )
                    hazards.append(hazard)
        
        return hazards
    
    def _analyze_physical_hazards(self, content: str) -> List[HazardAnalysis]:
        """Analyze physical hazards from content"""
        
        hazards = []
        
        physical_hazard_patterns = {
            "Высокая температура": [r'температур[аеы]\s*выше\s*\d+', r'нагрев', r'горяч'],
            "Электрическое напряжение": [r'напряжение', r'электричество', r'подключение\s+к\s+сети'],
            "Движущиеся части": [r'вращени', r'ротор', r'центрифуг', r'миксер'],
            "Острые предметы": [r'лезви', r'игл[аы]', r'скальпель', r'разбитое\s+стекло'],
            "Радиация": [r'радиац', r'излучение', r'рентген', r'гамма']
        }
        
        content_lower = content.lower()
        
        for hazard_name, patterns in physical_hazard_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    hazard = HazardAnalysis(
                        hazard_id=f"PHYS_{len(hazards)+1:03d}",
                        category=HazardCategory.PHYSICAL,
                        description=hazard_name,
                        risk_level=RiskLevel.MEDIUM,
                        probability="Medium",
                        severity="Moderate",
                        risk_rating=9,  # Medium × Moderate
                        regulatory_references=["ГОСТ 12.1.038-82", "ГОСТ 12.1.019-2017"],
                        control_measures=self._generate_physical_hazard_controls(hazard_name)
                    )
                    hazards.append(hazard)
                    break
        
        return hazards
    
    def _analyze_environmental_hazards(self, content: str) -> List[HazardAnalysis]:
        """Analyze environmental hazards"""
        
        hazards = []
        
        environmental_patterns = {
            "Загрязнение воздуха": [r'выброс', r'испарени', r'пары', r'аэрозол'],
            "Загрязнение воды": [r'слив', r'промывк', r'стоки'],
            "Отходы": [r'утилизац', r'отход[ыи]', r'отработанн']
        }
        
        content_lower = content.lower()
        
        for hazard_name, patterns in environmental_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    hazard = HazardAnalysis(
                        hazard_id=f"ENV_{len(hazards)+1:03d}",
                        category=HazardCategory.ENVIRONMENTAL,
                        description=hazard_name,
                        risk_level=RiskLevel.LOW,
                        probability="Low",
                        severity="Minor",
                        risk_rating=2,  # Low × Minor
                        regulatory_references=["ФЗ-7 'Об охране окружающей среды'", "СанПиН 2.1.3684-21"],
                        control_measures=self._generate_environmental_controls(hazard_name)
                    )
                    hazards.append(hazard)
                    break
        
        return hazards
    
    def generate_ppe_requirements(self, hazards: List[HazardAnalysis], operation_context: str = None) -> List[PPERequirement]:
        """Generate specific PPE requirements based on identified hazards"""
        
        ppe_requirements = []
        
        # Analyze required PPE types based on hazards
        required_ppe_types = set()
        
        for hazard in hazards:
            if hazard.category == HazardCategory.CHEMICAL:
                if any(keyword in hazard.description.lower() for keyword in ['кислот', 'щелоч', 'агрессивн']):
                    required_ppe_types.add(PPEType.EYE_PROTECTION)
                    required_ppe_types.add(PPEType.HAND_PROTECTION)
                    required_ppe_types.add(PPEType.BODY_PROTECTION)
                if any(keyword in hazard.description.lower() for keyword in ['пары', 'газ', 'аэрозол', 'токсич']):
                    required_ppe_types.add(PPEType.RESPIRATORY)
            
            elif hazard.category == HazardCategory.PHYSICAL:
                if any(keyword in hazard.description.lower() for keyword in ['уф', 'излучение', 'свет']):
                    required_ppe_types.add(PPEType.EYE_PROTECTION)
                if any(keyword in hazard.description.lower() for keyword in ['острый', 'режущ', 'колющ']):
                    required_ppe_types.add(PPEType.HAND_PROTECTION)
                if any(keyword in hazard.description.lower() for keyword in ['шум', 'звук']):
                    required_ppe_types.add(PPEType.HEARING_PROTECTION)
        
        # Generate specific PPE requirements
        for ppe_type in required_ppe_types:
            if ppe_type in self.ppe_database:
                # Select most appropriate PPE from database
                ppe_options = self.ppe_database[ppe_type]
                selected_ppe = self._select_appropriate_ppe(ppe_options, hazards, operation_context)
                
                ppe_req = PPERequirement(
                    ppe_type=ppe_type,
                    specification=selected_ppe["type"],
                    performance_standard=selected_ppe["standard"],
                    usage_conditions=", ".join(selected_ppe["applications"]),
                    replacement_criteria=selected_ppe["replacement"],
                    regulatory_standard=selected_ppe["standard"]
                )
                ppe_requirements.append(ppe_req)
        
        return ppe_requirements
    
    def generate_emergency_procedures_content(self, hazards: List[HazardAnalysis]) -> str:
        """Generate comprehensive emergency procedures content"""
        
        content = []
        content.append("## Аварийные процедуры и реагирование на чрезвычайные ситуации\n")
        
        # Determine relevant emergency scenarios
        relevant_scenarios = set()
        
        for hazard in hazards:
            if hazard.category == HazardCategory.CHEMICAL:
                relevant_scenarios.add("chemical_spill")
                if any(keyword in hazard.description.lower() for keyword in ['воспламен', 'горюч', 'взрыв']):
                    relevant_scenarios.add("fire_emergency")
            elif hazard.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                relevant_scenarios.add("injury_emergency")
        
        # Generate procedures for each relevant scenario
        for scenario_key in relevant_scenarios:
            if scenario_key in self.emergency_procedures:
                procedure = self.emergency_procedures[scenario_key]
                content.append(f"### {procedure.scenario}\n")
                
                content.append("#### Немедленные действия:")
                for i, action in enumerate(procedure.immediate_actions, 1):
                    content.append(f"{i}. **{action}**")
                content.append("")
                
                content.append("#### Порядок уведомления:")
                for i, notification in enumerate(procedure.notification_procedure, 1):
                    content.append(f"{i}. {notification}")
                content.append("")
                
                if procedure.evacuation_procedure:
                    content.append("#### Эвакуация:")
                    content.append(f"- {procedure.evacuation_procedure}\n")
                
                if procedure.cleanup_procedure:
                    content.append("#### Ликвидация последствий:")
                    content.append(f"- {procedure.cleanup_procedure}\n")
                
                content.append("#### Документирование:")
                for requirement in procedure.reporting_requirements:
                    content.append(f"- {requirement}")
                content.append("")
                
                content.append("#### Контактная информация:")
                for contact, phone in procedure.contact_information.items():
                    content.append(f"- **{contact}:** {phone}")
                content.append("")
        
        # Add general emergency equipment and supplies
        content.append("### Аварийное оборудование и материалы\n")
        content.append("**Обязательное наличие в лаборатории:**")
        content.append("☐ Аптечка первой помощи (состав по приказу 169н)")
        content.append("☐ Огнетушитель соответствующего класса")
        content.append("☐ Сорбент для локализации разливов")
        content.append("☐ Душ безопасности и промывка для глаз")
        content.append("☐ Средства нейтрализации кислот и щелочей")
        content.append("☐ Контейнеры для сбора опасных отходов")
        content.append("☐ Телефоны экстренных служб на видном месте")
        content.append("")
        
        # Emergency communication plan
        content.append("### План экстренного оповещения\n")
        content.append("#### Внутреннее оповещение:")
        content.append("1. Звуковая сигнализация в помещении")
        content.append("2. Голосовое оповещение присутствующего персонала")
        content.append("3. Уведомление по внутренней связи/телефону")
        content.append("")
        content.append("#### Внешнее оповещение:")
        content.append("1. Вызов экстренных служб (101, 103, 112)")
        content.append("2. Уведомление руководства организации")
        content.append("3. Информирование надзорных органов (при необходимости)")
        content.append("")
        
        return "\n".join(content)
    
    def generate_regulatory_compliance_content(self, hazards: List[HazardAnalysis], equipment_type: str = None) -> str:
        """Generate regulatory compliance content"""
        
        content = []
        content.append("## Нормативное обеспечение и соответствие требованиям\n")
        
        # Determine applicable standards
        applicable_standards = set(["GOST_12_1_005", "ISO_45001"])  # Always include these
        
        # Add equipment-specific standards
        if equipment_type and "chromatograph" in equipment_type.lower():
            applicable_standards.add("OSHA_1910")
        
        # Add hazard-specific standards based on identified hazards
        for hazard in hazards:
            if hazard.category == HazardCategory.CHEMICAL:
                applicable_standards.add("OSHA_1910")
        
        content.append("### Применимые нормативные документы\n")
        content.append("| Стандарт | Область применения | Ключевые требования |")
        content.append("|----------|-------------------|---------------------|")
        
        for standard_key in applicable_standards:
            if standard_key in self.regulatory_database:
                reg = self.regulatory_database[standard_key]
                requirements_brief = "; ".join(reg.compliance_requirements[:2])
                content.append(f"| {reg.standard_id} | {reg.title} | {requirements_brief} |")
        
        content.append("")
        
        # Detailed compliance requirements
        content.append("### Детальные требования соответствия\n")
        
        for standard_key in applicable_standards:
            if standard_key in self.regulatory_database:
                reg = self.regulatory_database[standard_key]
                
                content.append(f"#### {reg.standard_id}: {reg.title}")
                content.append(f"**Применимые разделы:** {', '.join(reg.applicable_sections)}")
                content.append("")
                
                content.append("**Требования соответствия:**")
                for req in reg.compliance_requirements:
                    content.append(f"- {req}")
                content.append("")
                
                content.append("**Необходимая документация:**")
                for doc in reg.documentation_needed:
                    content.append(f"☐ {doc}")
                content.append("")
                
                content.append(f"**Периодичность аудита:** {reg.audit_frequency}")
                content.append("")
        
        # Compliance monitoring
        content.append("### Мониторинг соответствия\n")
        content.append("#### Внутренний контроль:")
        content.append("1. **Ежедневный контроль:**")
        content.append("   - Проверка наличия и состояния СИЗ")
        content.append("   - Контроль работы вентиляции")
        content.append("   - Проверка аварийного оборудования")
        content.append("")
        
        content.append("2. **Еженедельный контроль:**")
        content.append("   - Проверка журналов инструктажей")
        content.append("   - Контроль состояния рабочих мест")
        content.append("   - Анализ отчетов о происшествиях")
        content.append("")
        
        content.append("3. **Ежемесячный контроль:**")
        content.append("   - Анализ эффективности мер безопасности")
        content.append("   - Проверка актуальности документации")
        content.append("   - Планирование корректирующих действий")
        content.append("")
        
        content.append("#### Внешний аудит:")
        content.append("- Подготовка к проверкам надзорных органов")
        content.append("- Сертификационные аудиты системы менеджмента")
        content.append("- Аккредитационные проверки лаборатории")
        content.append("")
        
        return "\n".join(content)
    
    def perform_comprehensive_safety_integration(self, sop_content: str, 
                                               equipment_type: str = None,
                                               chemicals: List[str] = None) -> Dict[str, Any]:
        """Perform comprehensive safety integration analysis"""
        
        # Perform hazard analysis
        hazards = self.analyze_hazards(sop_content, equipment_type, chemicals)
        
        # Generate PPE requirements
        ppe_requirements = self.generate_ppe_requirements(hazards, equipment_type)
        
        # Generate content sections
        emergency_content = self.generate_emergency_procedures_content(hazards)
        regulatory_content = self.generate_regulatory_compliance_content(hazards, equipment_type)
        ppe_content = self._generate_ppe_content(ppe_requirements)
        hazard_analysis_content = self._generate_hazard_analysis_content(hazards)
        
        return {
            "hazard_analysis": hazards,
            "ppe_requirements": ppe_requirements,
            "content_sections": {
                "hazard_analysis": hazard_analysis_content,
                "ppe_requirements": ppe_content,
                "emergency_procedures": emergency_content,
                "regulatory_compliance": regulatory_content
            },
            "safety_integration_score": self._calculate_safety_integration_score(hazards, ppe_requirements),
            "critical_safety_gaps": self._identify_critical_safety_gaps(sop_content, hazards)
        }
    
    def _generate_hazard_analysis_content(self, hazards: List[HazardAnalysis]) -> str:
        """Generate hazard analysis content for SOP"""
        
        content = []
        content.append("## Анализ опасных факторов и оценка рисков\n")
        
        # Risk matrix
        content.append("### Матрица оценки рисков\n")
        content.append("| ID | Опасный фактор | Категория | Уровень риска | Меры контроля |")
        content.append("|----|---------------|-----------|---------------|---------------|")
        
        for hazard in sorted(hazards, key=lambda x: x.risk_rating, reverse=True):
            measures = "; ".join(hazard.control_measures[:2])
            content.append(f"| {hazard.hazard_id} | {hazard.description} | {hazard.category.value} | {hazard.risk_level.value} | {measures} |")
        
        content.append("")
        
        # Critical risks detailed analysis
        critical_hazards = [h for h in hazards if h.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]]
        
        if critical_hazards:
            content.append("### Детальный анализ критических и высоких рисков\n")
            
            for hazard in critical_hazards:
                content.append(f"#### {hazard.hazard_id}: {hazard.description}")
                content.append(f"**Категория:** {hazard.category.value}")
                content.append(f"**Вероятность:** {hazard.probability}")
                content.append(f"**Тяжесть последствий:** {hazard.severity}")
                content.append(f"**Рейтинг риска:** {hazard.risk_rating}")
                content.append("")
                
                content.append("**Меры контроля:**")
                for measure in hazard.control_measures:
                    content.append(f"- {measure}")
                content.append("")
                
                if hazard.regulatory_references:
                    content.append("**Нормативные ссылки:**")
                    for ref in hazard.regulatory_references:
                        content.append(f"- {ref}")
                    content.append("")
        
        return "\n".join(content)
    
    def _generate_ppe_content(self, ppe_requirements: List[PPERequirement]) -> str:
        """Generate PPE requirements content"""
        
        content = []
        content.append("## Средства индивидуальной защиты (СИЗ)\n")
        
        if not ppe_requirements:
            content.append("**Примечание:** Специальные СИЗ не требуются для данной процедуры. Используйте стандартные лабораторные СИЗ.\n")
            return "\n".join(content)
        
        content.append("### Обязательные требования к СИЗ\n")
        content.append("| Тип СИЗ | Спецификация | Стандарт | Условия применения | Критерии замены |")
        content.append("|---------|-------------|----------|-------------------|-----------------|")
        
        for ppe in ppe_requirements:
            content.append(f"| {ppe.ppe_type.value} | {ppe.specification} | {ppe.performance_standard} | {ppe.usage_conditions} | {ppe.replacement_criteria} |")
        
        content.append("")
        
        # Detailed PPE instructions
        content.append("### Инструкции по использованию СИЗ\n")
        
        for i, ppe in enumerate(ppe_requirements, 1):
            content.append(f"#### {i}. {ppe.specification}")
            content.append(f"**Стандарт:** {ppe.performance_standard}")
            content.append(f"**Применение:** {ppe.usage_conditions}")
            content.append(f"**Замена:** {ppe.replacement_criteria}")
            content.append("")
            
            # Add specific usage instructions
            content.append("**Порядок использования:**")
            if ppe.ppe_type == PPEType.HAND_PROTECTION:
                content.append("1. Проверить целостность перчаток перед надеванием")
                content.append("2. Надевать на сухие, чистые руки")
                content.append("3. Снимать, не касаясь внешней поверхности")
                content.append("4. Немедленная замена при повреждении или контаминации")
            elif ppe.ppe_type == PPEType.EYE_PROTECTION:
                content.append("1. Очистить линзы перед использованием")
                content.append("2. Обеспечить плотное прилегание к лицу")
                content.append("3. Хранить в защитном футляре")
                content.append("4. Регулярная дезинфекция согласно инструкции")
            
            content.append("")
        
        # PPE maintenance and storage
        content.append("### Техническое обслуживание и хранение СИЗ\n")
        content.append("**Ежедневные требования:**")
        content.append("☐ Визуальный осмотр СИЗ перед использованием")
        content.append("☐ Очистка после использования")
        content.append("☐ Проверка сроков годности")
        content.append("")
        
        content.append("**Еженедельные требования:**")
        content.append("☐ Инвентаризация запаса СИЗ")
        content.append("☐ Проверка условий хранения")
        content.append("☐ Планирование закупок")
        content.append("")
        
        return "\n".join(content)
    
    # Helper methods
    def _detect_chemicals_in_content(self, content: str) -> List[str]:
        """Detect chemical names in SOP content"""
        chemical_patterns = [
            r'кислот[аы]?\s+\w+',
            r'щелоч[ьи]?\s+\w+',
            r'растворитель\s+\w+',
            r'реагент\s+\w+',
            r'\b[A-Za-z]{3,}\s*-?\s*\d{2,}[A-Za-z]?\b'  # Chemical formulas
        ]
        
        chemicals = []
        content_lower = content.lower()
        
        for pattern in chemical_patterns:
            matches = re.findall(pattern, content_lower)
            chemicals.extend(matches)
        
        return list(set(chemicals))[:10]  # Limit to 10 unique chemicals
    
    def _assess_risk_level(self, hazard_desc: str, content: str) -> RiskLevel:
        """Assess risk level based on hazard description and context"""
        high_risk_keywords = ['токсичн', 'коррози', 'взрыв', 'пожар', 'смерт']
        medium_risk_keywords = ['вредн', 'раздражен', 'аллерги']
        
        hazard_lower = hazard_desc.lower()
        
        if any(keyword in hazard_lower for keyword in high_risk_keywords):
            return RiskLevel.HIGH
        elif any(keyword in hazard_lower for keyword in medium_risk_keywords):
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _assess_severity(self, hazard_desc: str) -> str:
        """Assess severity of hazard"""
        if any(keyword in hazard_desc.lower() for keyword in ['смерт', 'критич', 'тяжел']):
            return "Major"
        elif any(keyword in hazard_desc.lower() for keyword in ['коррози', 'ожог', 'отравлен']):
            return "Moderate"
        else:
            return "Minor"
    
    def _calculate_risk_rating(self, probability: str, severity: str) -> int:
        """Calculate risk rating using probability × severity matrix"""
        prob_values = {"Very Low": 1, "Low": 2, "Medium": 3, "High": 4, "Very High": 5}
        sev_values = {"Negligible": 1, "Minor": 2, "Moderate": 3, "Major": 4, "Catastrophic": 5}
        
        return prob_values.get(probability, 3) * sev_values.get(severity, 2)
    
    def _severity_to_risk_level(self, severity: str) -> RiskLevel:
        """Convert severity to risk level"""
        severity_map = {
            "Major": RiskLevel.HIGH,
            "Moderate": RiskLevel.MEDIUM,
            "Minor": RiskLevel.LOW
        }
        return severity_map.get(severity, RiskLevel.MEDIUM)
    
    def _generate_control_measures(self, hazard_desc: str, chemical: str) -> List[str]:
        """Generate control measures for specific hazards"""
        measures = []
        
        hazard_lower = hazard_desc.lower()
        
        if 'коррози' in hazard_lower:
            measures.extend([
                "Использование химически стойких СИЗ",
                "Работа в вытяжном шкафу",
                "Наличие души безопасности и промывки для глаз",
                "Процедуры нейтрализации разливов"
            ])
        elif 'токсич' in hazard_lower:
            measures.extend([
                "Обеспечение местной вытяжной вентиляции",
                "Использование респираторов при необходимости",
                "Регулярный контроль концентраций в воздухе",
                "Медицинские осмотры персонала"
            ])
        elif 'воспламен' in hazard_lower:
            measures.extend([
                "Исключение источников воспламенения",
                "Использование взрывобезопасного оборудования",
                "Система пожарной сигнализации",
                "Наличие соответствующих огнетушителей"
            ])
        
        # Generic measures
        measures.extend([
            "Обучение персонала безопасным методам работы",
            "Регулярные инструктажи по охране труда",
            "Ведение документации по безопасности"
        ])
        
        return measures[:5]  # Limit to 5 measures
    
    def _generate_equipment_controls(self, hazard_name: str, consequences: List[str]) -> List[str]:
        """Generate equipment-specific control measures"""
        controls = []
        
        if "давление" in hazard_name.lower():
            controls.extend([
                "Регулярная проверка состояния фитингов и соединений",
                "Использование предохранительных клапанов",
                "Обучение персонала безопасным методам работы с давлением",
                "Процедуры сброса давления перед обслуживанием"
            ])
        elif "излучение" in hazard_name.lower():
            controls.extend([
                "Использование УФ-защитных очков",
                "Ограничение времени воздействия",
                "Экранирование источников излучения",
                "Регулярный контроль уровней излучения"
            ])
        elif "температур" in hazard_name.lower():
            controls.extend([
                "Использование термозащитных СИЗ",
                "Процедуры безопасного охлаждения",
                "Маркировка горячих поверхностей",
                "Обучение первой помощи при ожогах"
            ])
        
        return controls
    
    def _generate_physical_hazard_controls(self, hazard_name: str) -> List[str]:
        """Generate physical hazard control measures"""
        control_map = {
            "Высокая температура": [
                "Термозащитные СИЗ",
                "Процедуры безопасного охлаждения",
                "Маркировка горячих поверхностей"
            ],
            "Электрическое напряжение": [
                "Проверка заземления оборудования",
                "Использование УЗО",
                "Обучение электробезопасности"
            ],
            "Движущиеся части": [
                "Защитные ограждения",
                "Процедуры ЛОТО",
                "Блокировочные устройства"
            ],
            "Острые предметы": [
                "Защитные перчатки",
                "Безопасная утилизация острых отходов",
                "Первая помощь при порезах"
            ],
            "Радиация": [
                "Дозиметрический контроль",
                "Радиационная защита",
                "Медицинское наблюдение персонала"
            ]
        }
        
        return control_map.get(hazard_name, ["Общие меры безопасности", "Обучение персонала"])
    
    def _generate_environmental_controls(self, hazard_name: str) -> List[str]:
        """Generate environmental hazard controls"""
        control_map = {
            "Загрязнение воздуха": [
                "Местная вытяжная вентиляция",
                "Контроль выбросов",
                "Фильтрация отходящих газов"
            ],
            "Загрязнение воды": [
                "Очистка сточных вод",
                "Контроль качества стоков",
                "Предотвращение попадания в канализацию"
            ],
            "Отходы": [
                "Раздельный сбор отходов",
                "Лицензированная утилизация",
                "Минимизация образования отходов"
            ]
        }
        
        return control_map.get(hazard_name, ["Экологический мониторинг", "Соблюдение природоохранного законодательства"])
    
    def _select_appropriate_ppe(self, ppe_options: List[Dict[str, Any]], hazards: List[HazardAnalysis], context: str) -> Dict[str, Any]:
        """Select most appropriate PPE based on hazards and context"""
        
        # Simple selection logic - can be enhanced with more sophisticated matching
        for ppe in ppe_options:
            # Check if PPE applications match identified hazards
            for hazard in hazards:
                if any(app_keyword in hazard.description.lower() for app_keyword in ppe["applications"]):
                    return ppe
        
        # Return first option as default
        return ppe_options[0] if ppe_options else {}
    
    def _calculate_safety_integration_score(self, hazards: List[HazardAnalysis], ppe_requirements: List[PPERequirement]) -> int:
        """Calculate overall safety integration score"""
        
        base_score = 70
        
        # Add points for hazard identification
        hazard_bonus = min(len(hazards) * 2, 15)
        
        # Add points for PPE coverage
        ppe_bonus = min(len(ppe_requirements) * 3, 10)
        
        # Add points for regulatory coverage
        regulatory_bonus = 5  # Assume basic regulatory coverage
        
        return min(base_score + hazard_bonus + ppe_bonus + regulatory_bonus, 100)
    
    def _identify_critical_safety_gaps(self, sop_content: str, hazards: List[HazardAnalysis]) -> List[str]:
        """Identify critical safety gaps in current SOP"""
        
        gaps = []
        
        # Check for missing emergency procedures
        if not re.search(r'аварий|чрезвычай|экстрен', sop_content.lower()):
            gaps.append("Отсутствуют процедуры реагирования на аварийные ситуации")
        
        # Check for missing PPE information
        if not re.search(r'сиз|защитн.*средств|перчатк|очк', sop_content.lower()):
            gaps.append("Недостаточная информация о требуемых СИЗ")
        
        # Check for high-risk hazards without adequate controls
        critical_hazards = [h for h in hazards if h.risk_level == RiskLevel.CRITICAL]
        if critical_hazards and len(critical_hazards) > 2:
            gaps.append("Выявлены критические риски, требующие дополнительных мер контроля")
        
        # Check for missing regulatory references
        if not re.search(r'гост|санпин|iso|стандарт', sop_content.lower()):
            gaps.append("Отсутствуют ссылки на применимые стандарты безопасности")
        
        return gaps