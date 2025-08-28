from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re
import json


class EquipmentType(Enum):
    CHROMATOGRAPHY = "chromatography"
    SPECTROSCOPY = "spectroscopy"
    MICROSCOPY = "microscopy"
    ANALYTICAL_BALANCE = "analytical_balance"
    CENTRIFUGE = "centrifuge"
    THERMAL_ANALYZER = "thermal_analyzer"
    GENERIC_ANALYTICAL = "generic_analytical"


@dataclass
class EquipmentSpecification:
    """Professional equipment specification template"""
    equipment_type: EquipmentType
    common_models: List[str]
    critical_parameters: List[Dict[str, Any]]
    calibration_requirements: List[Dict[str, Any]]
    maintenance_procedures: List[Dict[str, Any]]
    safety_considerations: List[str]
    troubleshooting_guide: List[Dict[str, Any]]
    regulatory_standards: List[str]


class ProfessionalEquipmentEngine:
    """Professional equipment-specific content generation system"""
    
    def __init__(self):
        self.equipment_database = self._initialize_equipment_database()
        
    def _initialize_equipment_database(self) -> Dict[EquipmentType, EquipmentSpecification]:
        """Initialize professional equipment specifications database"""
        
        return {
            EquipmentType.CHROMATOGRAPHY: EquipmentSpecification(
                equipment_type=EquipmentType.CHROMATOGRAPHY,
                common_models=[
                    "Agilent 1260 Infinity II LC",
                    "Waters ACQUITY UPLC H-Class",
                    "Shimadzu LC-2030C 3D Plus",
                    "Thermo Scientific UltiMate 3000",
                    "PerkinElmer Flexar FX-10"
                ],
                critical_parameters=[
                    {
                        "parameter": "Скорость потока",
                        "range": "0.1-10.0 мл/мин",
                        "tolerance": "±2%",
                        "units": "мл/мин",
                        "typical_values": ["1.0", "1.5", "2.0"]
                    },
                    {
                        "parameter": "Температура колонки",
                        "range": "10-80°C",
                        "tolerance": "±1°C",
                        "units": "°C", 
                        "typical_values": ["25", "30", "40"]
                    },
                    {
                        "parameter": "Давление системы",
                        "range": "0-600 бар",
                        "tolerance": "±5 бар",
                        "units": "бар",
                        "typical_values": ["150", "200", "300"]
                    },
                    {
                        "parameter": "Объем инъекции",
                        "range": "0.1-100 мкл",
                        "tolerance": "±1%",
                        "units": "мкл",
                        "typical_values": ["5", "10", "20"]
                    }
                ],
                calibration_requirements=[
                    {
                        "procedure": "Калибровка объема инъекции",
                        "frequency": "ежемесячно",
                        "standard": "Certified volume standards",
                        "acceptance": "±2% от номинального значения"
                    },
                    {
                        "procedure": "Проверка градиента",
                        "frequency": "еженедельно",
                        "standard": "Caffeine/Uracil test mix",
                        "acceptance": "Время удерживания ±5%, площадь пика ±10%"
                    },
                    {
                        "procedure": "Калибровка детектора",
                        "frequency": "ежемесячно",
                        "standard": "Holmium oxide filter (UV), Caffeine (DAD)",
                        "acceptance": "Максимум поглощения 279.3±2 нм"
                    }
                ],
                maintenance_procedures=[
                    {
                        "task": "Замена мобильной фазы",
                        "frequency": "еженедельно или по мере необходимости",
                        "procedure": "Промывка линий, замена растворителей, дегазация"
                    },
                    {
                        "task": "Очистка инжектора",
                        "frequency": "еженедельно",
                        "procedure": "Промывка seat capillary, замена уплотнений"
                    },
                    {
                        "task": "Проверка фильтров",
                        "frequency": "ежемесячно",
                        "procedure": "Замена inlet filter, проверка column inlet filter"
                    }
                ],
                safety_considerations=[
                    "Работа с токсичными растворителями в вытяжном шкафу",
                    "СИЗ: защитные очки, нитриловые перчатки, лабораторный халат",
                    "Высокое давление: не снимать фитинги под давлением",
                    "Пожароопасность: ацетонитрил, метанол - класс 1B",
                    "Утилизация отработанных растворителей согласно SDS"
                ],
                troubleshooting_guide=[
                    {
                        "problem": "Высокое давление системы",
                        "symptoms": "Превышение 400 бар при стандартных условиях",
                        "causes": ["Засорение колонки", "Засорение фильтров", "Высокая вязкость мобильной фазы"],
                        "solutions": ["Обратная промывка колонки", "Замена inlet filter", "Проверка состава мобильной фазы"]
                    },
                    {
                        "problem": "Дрейф базовой линии",
                        "symptoms": "Нестабильная базовая линия детектора",
                        "causes": ["Пузыри в системе", "Загрязнение лампы", "Нестабильная температура"],
                        "solutions": ["Дегазация мобильной фазы", "Очистка/замена лампы", "Проверка термостата"]
                    }
                ],
                regulatory_standards=[
                    "ГОСТ 31640-2012 (Хроматография)",
                    "ICH Q2(R1) Validation of Analytical Procedures", 
                    "ISO 17025:2017 General requirements for testing laboratories",
                    "USP <621> Chromatography"
                ]
            ),
            
            EquipmentType.SPECTROSCOPY: EquipmentSpecification(
                equipment_type=EquipmentType.SPECTROSCOPY,
                common_models=[
                    "PerkinElmer Lambda 950 UV/Vis",
                    "Agilent Cary 60 UV-Vis",
                    "Shimadzu UV-2700",
                    "Thermo Scientific Evolution 220",
                    "Hach DR3900 Spectrophotometer"
                ],
                critical_parameters=[
                    {
                        "parameter": "Длина волны",
                        "range": "190-1100 нм",
                        "tolerance": "±1 нм",
                        "units": "нм",
                        "typical_values": ["254", "280", "340", "540"]
                    },
                    {
                        "parameter": "Спектральная ширина щели",
                        "range": "0.5-5.0 нм",
                        "tolerance": "±0.1 нм",
                        "units": "нм",
                        "typical_values": ["1.0", "2.0"]
                    },
                    {
                        "parameter": "Абсорбция",
                        "range": "-0.3-3.0 A",
                        "tolerance": "±0.002 A",
                        "units": "A",
                        "typical_values": ["0.5", "1.0", "1.5"]
                    }
                ],
                calibration_requirements=[
                    {
                        "procedure": "Проверка длины волны",
                        "frequency": "ежемесячно",
                        "standard": "Holmium oxide filter",
                        "acceptance": "Пики при 279.3, 360.8, 453.4 нм ±2 нм"
                    },
                    {
                        "procedure": "Проверка абсорбции",
                        "frequency": "ежемесячно",
                        "standard": "Neutral density filters",
                        "acceptance": "±2% от номинального значения"
                    },
                    {
                        "procedure": "Проверка стрей-света",
                        "frequency": "раз в полгода",
                        "standard": "NaI 220 нм, NaNO2 340 нм",
                        "acceptance": "<0.05% T"
                    }
                ],
                maintenance_procedures=[
                    {
                        "task": "Очистка кювет",
                        "frequency": "после каждого использования",
                        "procedure": "Промывка дистиллированной водой, сушка безворсовой салфеткой"
                    },
                    {
                        "task": "Замена лампы",
                        "frequency": "по индикатору или при снижении интенсивности",
                        "procedure": "Выключение, остывание, замена согласно инструкции"
                    }
                ],
                safety_considerations=[
                    "УФ излучение: защитные очки, избегать прямого воздействия",
                    "Кварцевые кюветы: осторожность при обращении",
                    "Растворители: работа в вытяжном шкафу",
                    "СИЗ: УФ-защитные очки, перчатки, халат"
                ],
                troubleshooting_guide=[
                    {
                        "problem": "Низкая интенсивность лампы",
                        "symptoms": "Сигнал ниже нормы, высокий шум",
                        "causes": ["Старение лампы", "Загрязнение оптики", "Неправильная юстировка"],
                        "solutions": ["Замена лампы", "Очистка оптических элементов", "Юстировка системы"]
                    }
                ],
                regulatory_standards=[
                    "ГОСТ 8.207-76 Фотометры спектральные",
                    "ICH Q2(R1) Validation of Analytical Procedures",
                    "USP <857> Ultraviolet-Visible Spectroscopy"
                ]
            ),
            
            EquipmentType.ANALYTICAL_BALANCE: EquipmentSpecification(
                equipment_type=EquipmentType.ANALYTICAL_BALANCE,
                common_models=[
                    "Mettler Toledo XPE205",
                    "Sartorius Cubis II MSA225S",
                    "Shimadzu AUW220D",
                    "OHAUS Discovery DV215CD",
                    "A&D HR-250AZ"
                ],
                critical_parameters=[
                    {
                        "parameter": "Максимальная нагрузка",
                        "range": "0-220 г",
                        "tolerance": "±0.1 мг",
                        "units": "г",
                        "typical_values": ["100", "150", "200"]
                    },
                    {
                        "parameter": "Дискретность отсчета",
                        "range": "0.01-0.1 мг",
                        "tolerance": "±0.01 мг",
                        "units": "мг",
                        "typical_values": ["0.1"]
                    },
                    {
                        "parameter": "Время установления показаний",
                        "range": "3-8 сек",
                        "tolerance": "±1 сек",
                        "units": "сек",
                        "typical_values": ["5"]
                    }
                ],
                calibration_requirements=[
                    {
                        "procedure": "Внешняя калибровка",
                        "frequency": "ежедневно",
                        "standard": "Сертифицированные гири класса E1/E2",
                        "acceptance": "Разность не более 0.3 мг для 200г гири"
                    },
                    {
                        "procedure": "Проверка линейности",
                        "frequency": "ежемесячно",
                        "standard": "Набор гирь 10%, 50%, 100% диапазона",
                        "acceptance": "Отклонение не более ±0.5 мг"
                    },
                    {
                        "procedure": "Проверка эксцентриситета",
                        "frequency": "ежемесячно", 
                        "standard": "Гиря 1/3 максимальной нагрузки",
                        "acceptance": "Разность показаний не более 1 мг"
                    }
                ],
                maintenance_procedures=[
                    {
                        "task": "Очистка чашки весов",
                        "frequency": "ежедневно",
                        "procedure": "Снятие статического заряда, очистка безворсовой салфеткой"
                    },
                    {
                        "task": "Проверка уровня",
                        "frequency": "еженедельно",
                        "procedure": "Контроль положения пузырька уровня, корректировка"
                    }
                ],
                safety_considerations=[
                    "Устойчивая установка на антивибрационном столе",
                    "Защита от воздушных потоков и температурных колебаний",
                    "СИЗ: антистатические перчатки при работе с органикой",
                    "Осторожность с химически агрессивными веществами"
                ],
                troubleshooting_guide=[
                    {
                        "problem": "Нестабильные показания",
                        "symptoms": "Дрейф показаний, медленная стабилизация",
                        "causes": ["Вибрации", "Воздушные потоки", "Статическое электричество"],
                        "solutions": ["Проверка установки", "Закрытие ветрозащиты", "Ионизация воздуха"]
                    }
                ],
                regulatory_standards=[
                    "ГОСТ 24104-2001 Весы лабораторные",
                    "OIML R 76-1 Non-automatic weighing instruments",
                    "USP <41> Balances"
                ]
            )
        }
    
    def identify_equipment_type(self, equipment_description: str, reference_docs: List[str] = None) -> EquipmentType:
        """Identify equipment type from description and reference documents"""
        
        description_lower = equipment_description.lower()
        
        # Equipment type detection patterns
        type_patterns = {
            EquipmentType.CHROMATOGRAPHY: [
                r'хроматограф|chromatograph|hplc|uplc|gc|lc-ms',
                r'колонка|column|mobile phase|мобильная фаза',
                r'инжектор|detector|детектор|элю[еи]нт'
            ],
            EquipmentType.SPECTROSCOPY: [
                r'спектрометр|spectrometer|спектрофотометр|spectrophotometer',
                r'uv-vis|ик-спектр|ir spectrum|ftir',
                r'абсорбция|absorption|длина волны|wavelength'
            ],
            EquipmentType.MICROSCOPY: [
                r'микроскоп|microscope',
                r'объектив|objective|окуляр|eyepiece',
                r'увеличение|magnification|разрешение|resolution'
            ],
            EquipmentType.ANALYTICAL_BALANCE: [
                r'весы|balance|баланс',
                r'аналитические|analytical|точность|accuracy',
                r'гири|weights|калибровка|calibration'
            ],
            EquipmentType.CENTRIFUGE: [
                r'центрифуга|centrifuge',
                r'ротор|rotor|об/мин|rpm',
                r'пробирки|tubes|осадок|pellet'
            ],
            EquipmentType.THERMAL_ANALYZER: [
                r'термоанализ|thermal analysis|dsc|tga|dta',
                r'температурная программа|temperature program',
                r'тепловой поток|heat flow|масса|mass'
            ]
        }
        
        # Score each equipment type
        scores = {}
        for eq_type, patterns in type_patterns.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, description_lower, re.IGNORECASE)
                score += len(matches)
            scores[eq_type] = score
        
        # Check reference documents if available
        if reference_docs:
            for doc_content in reference_docs:
                doc_lower = doc_content.lower()
                for eq_type, patterns in type_patterns.items():
                    for pattern in patterns:
                        matches = re.findall(pattern, doc_lower, re.IGNORECASE)
                        scores[eq_type] += len(matches) * 2  # Weight reference docs higher
        
        # Return type with highest score
        if max(scores.values()) > 0:
            return max(scores.items(), key=lambda x: x[1])[0]
        else:
            return EquipmentType.GENERIC_ANALYTICAL
    
    def extract_equipment_context(self, reference_content: str) -> Dict[str, Any]:
        """Extract equipment-specific context from reference documents"""
        
        context = {
            "models": [],
            "specifications": {},
            "procedures": [],
            "parameters": {},
            "safety_info": []
        }
        
        # Extract model information
        model_patterns = [
            r'модель[:\s]+([A-Z][A-Za-z0-9\s-]+\d+[A-Za-z]*)',
            r'model[:\s]+([A-Z][A-Za-z0-9\s-]+\d+[A-Za-z]*)',
            r'([A-Z][a-z]+\s+[A-Z0-9-]+)',  # Brand Model
        ]
        
        for pattern in model_patterns:
            matches = re.findall(pattern, reference_content, re.IGNORECASE)
            context["models"].extend([m.strip() for m in matches[:5]])
        
        # Extract technical parameters
        param_patterns = [
            r'(температур[аы])[:\s]*(\d+(?:\.\d+)?)\s*[°℃]?([CF]?)',
            r'(давлени[ея])[:\s]*(\d+(?:\.\d+)?)\s*(бар|bar|кПа|МПа|атм)',
            r'(скорость)[:\s]*(\d+(?:\.\d+)?)\s*(мл/мин|ml/min|об/мин|rpm)',
            r'(время)[:\s]*(\d+(?:\.\d+)?)\s*(мин|min|сек|sec|час|hr)',
            r'(объ[её]м)[:\s]*(\d+(?:\.\d+)?)\s*(мл|ml|л|L|мкл|μL)'
        ]
        
        for pattern in param_patterns:
            matches = re.findall(pattern, reference_content, re.IGNORECASE)
            for match in matches[:10]:
                param_name, value, unit = match
                if param_name not in context["parameters"]:
                    context["parameters"][param_name] = []
                context["parameters"][param_name].append({
                    "value": value,
                    "unit": unit
                })
        
        # Extract safety information
        safety_patterns = [
            r'осторожно[:\s]*(.*?)(?:\.|!|\n)',
            r'внимание[:\s]*(.*?)(?:\.|!|\n)',
            r'предупреждение[:\s]*(.*?)(?:\.|!|\n)',
            r'опасность[:\s]*(.*?)(?:\.|!|\n)'
        ]
        
        for pattern in safety_patterns:
            matches = re.findall(pattern, reference_content, re.IGNORECASE)
            context["safety_info"].extend([m.strip() for m in matches[:5]])
        
        return context
    
    def generate_equipment_specific_content(self, 
                                          equipment_type: EquipmentType, 
                                          section_type: str,
                                          context: Dict[str, Any] = None) -> str:
        """Generate professional equipment-specific content for SOP sections"""
        
        if equipment_type not in self.equipment_database:
            equipment_type = EquipmentType.GENERIC_ANALYTICAL
            
        spec = self.equipment_database[equipment_type]
        context = context or {}
        
        if section_type == "equipment_specifications":
            return self._generate_equipment_specifications(spec, context)
        elif section_type == "operating_procedures":
            return self._generate_operating_procedures(spec, context)
        elif section_type == "calibration_procedures":
            return self._generate_calibration_procedures(spec, context)
        elif section_type == "maintenance_procedures":
            return self._generate_maintenance_procedures(spec, context)
        elif section_type == "safety_procedures":
            return self._generate_safety_procedures(spec, context)
        elif section_type == "troubleshooting":
            return self._generate_troubleshooting_guide(spec, context)
        elif section_type == "quality_control":
            return self._generate_quality_control(spec, context)
        else:
            return self._generate_generic_section(spec, section_type, context)
    
    def _generate_equipment_specifications(self, spec: EquipmentSpecification, context: Dict[str, Any]) -> str:
        """Generate detailed equipment specifications section"""
        
        content = []
        
        # Equipment identification
        content.append("## Спецификация оборудования\n")
        
        if context.get("models"):
            content.append(f"**Модель:** {', '.join(context['models'][:3])}\n")
        else:
            content.append(f"**Рекомендуемые модели:** {', '.join(spec.common_models[:3])}\n")
        
        # Technical specifications table
        content.append("### Технические характеристики\n")
        content.append("| Параметр | Диапазон | Допуск | Типовые значения |")
        content.append("|----------|----------|---------|------------------|")
        
        for param in spec.critical_parameters:
            typical = ", ".join(param["typical_values"])
            content.append(f"| {param['parameter']} | {param['range']} | {param['tolerance']} | {typical} {param['units']} |")
        
        content.append("")
        
        # Required accessories
        content.append("### Необходимые принадлежности\n")
        content.append("☐ Расходные материалы согласно спецификации производителя")
        content.append("☐ Стандартные образцы для калибровки")
        content.append("☐ Программное обеспечение последней версии")
        content.append("☐ Документация: руководство пользователя, сертификаты")
        content.append("")
        
        return "\n".join(content)
    
    def _generate_operating_procedures(self, spec: EquipmentSpecification, context: Dict[str, Any]) -> str:
        """Generate detailed operating procedures"""
        
        content = []
        content.append("## Операционные процедуры\n")
        
        # Pre-operation checklist
        content.append("### Предэксплуатационная проверка\n")
        content.append("1. **Визуальный осмотр оборудования**")
        content.append("   - Проверка целостности корпуса и соединений")
        content.append("   - Отсутствие видимых повреждений")
        content.append("   - **Критерий приемки:** Нет трещин, протечек, повреждений\n")
        
        content.append("2. **Проверка подключения к сети**")
        content.append("   - Напряжение питания: 220В ± 10%")
        content.append("   - Заземление: сопротивление < 4 Ом")
        content.append("   - **Критерий приемки:** Стабильное электропитание\n")
        
        # Operating parameters setup
        content.append("### Настройка рабочих параметров\n")
        for i, param in enumerate(spec.critical_parameters[:4], 3):
            content.append(f"{i}. **{param['parameter']}**")
            content.append(f"   - Установить значение: {param['typical_values'][0]} {param['units']}")
            content.append(f"   - Допустимый диапазон: {param['range']}")
            content.append(f"   - **Критерий приемки:** Значение в пределах {param['tolerance']}\n")
        
        # Quality control during operation
        content.append("### Контроль в процессе работы\n")
        step = len(spec.critical_parameters) + 3
        content.append(f"{step}. **Мониторинг критических параметров**")
        content.append("   - Частота контроля: каждые 30 минут")
        content.append("   - Регистрация в журнале наблюдений")
        content.append("   - **Действие при отклонении:** Остановка процесса, диагностика\n")
        
        content.append(f"{step+1}. **Контроль качества результатов**")
        content.append("   - Проверка контрольного образца каждые 10 измерений")
        content.append("   - **Критерий приемки:** Отклонение не более ±5% от аттестованного значения")
        content.append("   - **При превышении допуска:** Повторная калибровка\n")
        
        return "\n".join(content)
    
    def _generate_calibration_procedures(self, spec: EquipmentSpecification, context: Dict[str, Any]) -> str:
        """Generate calibration procedures"""
        
        content = []
        content.append("## Процедуры калибровки и поверки\n")
        
        content.append("### График калибровочных работ\n")
        content.append("| Процедура | Периодичность | Стандартный образец | Критерии приемки |")
        content.append("|-----------|---------------|---------------------|------------------|")
        
        for calib in spec.calibration_requirements:
            content.append(f"| {calib['procedure']} | {calib['frequency']} | {calib['standard']} | {calib['acceptance']} |")
        
        content.append("")
        
        # Detailed calibration procedure
        content.append("### Процедура калибровки (детальная)\n")
        for i, calib in enumerate(spec.calibration_requirements, 1):
            content.append(f"{i}. **{calib['procedure']}**")
            content.append(f"   - **Периодичность:** {calib['frequency']}")
            content.append(f"   - **Стандарт:** {calib['standard']}")
            content.append("   - **Порядок выполнения:**")
            content.append("     1. Подготовка стандартного образца")
            content.append("     2. Установка стандартных условий измерения")
            content.append("     3. Выполнение серии измерений (n≥5)")
            content.append("     4. Статистическая обработка результатов")
            content.append("     5. Сравнение с критериями приемки")
            content.append(f"   - **Критерий приемки:** {calib['acceptance']}")
            content.append("   - **При несоответствии:** Техническое обслуживание, повторная калибровка\n")
        
        # Calibration records
        content.append("### Документирование калибровки\n")
        content.append("**Обязательная информация в протоколе калибровки:**")
        content.append("☐ Дата и время проведения")
        content.append("☐ Идентификационные данные оборудования")
        content.append("☐ Условия окружающей среды (T, RH, P)")
        content.append("☐ Используемые стандартные образцы")
        content.append("☐ Результаты измерений и расчетов")
        content.append("☐ Заключение о соответствии/несоответствии")
        content.append("☐ Подпись ответственного лица")
        content.append("")
        
        return "\n".join(content)
    
    def _generate_troubleshooting_guide(self, spec: EquipmentSpecification, context: Dict[str, Any]) -> str:
        """Generate troubleshooting guide"""
        
        content = []
        content.append("## Устранение неисправностей\n")
        
        content.append("### Диагностический алгоритм\n")
        
        for i, issue in enumerate(spec.troubleshooting_guide, 1):
            content.append(f"#### {i}. {issue['problem']}\n")
            
            content.append("**Симптомы:**")
            content.append(f"- {issue['symptoms']}\n")
            
            content.append("**Возможные причины:**")
            for cause in issue['causes']:
                content.append(f"- {cause}")
            content.append("")
            
            content.append("**Способы устранения:**")
            for j, solution in enumerate(issue['solutions'], 1):
                content.append(f"{j}. {solution}")
                content.append("   - Проверить эффективность")
                content.append("   - Зафиксировать результат в журнале")
            content.append("")
            
            content.append("**Критерий устранения проблемы:**")
            content.append("Возврат всех параметров в нормальные пределы\n")
        
        # Emergency procedures
        content.append("### Аварийные ситуации\n")
        content.append("#### Действия при критических неисправностях:\n")
        content.append("1. **НЕМЕДЛЕННО остановить оборудование**")
        content.append("2. **Обесточить систему** (если безопасно)")
        content.append("3. **Уведомить ответственное лицо**")
        content.append("4. **Заполнить уведомление о происшествии**")
        content.append("5. **Не возобновлять работу** до устранения причины\n")
        
        content.append("**Контактная информация:**")
        content.append("- Техническая поддержка: [указать телефон]")
        content.append("- Сервисная служба: [указать телефон]")
        content.append("- Руководитель лаборатории: [указать телефон]")
        content.append("")
        
        return "\n".join(content)
        
    def _generate_safety_procedures(self, spec: EquipmentSpecification, context: Dict[str, Any]) -> str:
        """Generate comprehensive safety procedures"""
        
        content = []
        content.append("## Меры безопасности\n")
        
        content.append("### Анализ опасных факторов\n")
        for i, safety_item in enumerate(spec.safety_considerations, 1):
            content.append(f"{i}. {safety_item}")
        content.append("")
        
        # Add context-specific safety information
        if context.get("safety_info"):
            content.append("### Дополнительные меры предосторожности\n")
            for safety_info in context["safety_info"][:5]:
                content.append(f"- {safety_info}")
            content.append("")
        
        content.append("### Средства индивидуальной защиты\n")
        content.append("| Операция | Обязательные СИЗ | Дополнительные требования |")
        content.append("|----------|------------------|---------------------------|")
        
        # Equipment-specific PPE requirements
        if spec.equipment_type == EquipmentType.CHROMATOGRAPHY:
            content.append("| Подготовка мобильной фазы | Очки, перчатки нитрил, халат | Работа в вытяжном шкафу |")
            content.append("| Замена колонки | Очки, перчатки, халат | Осторожность с высоким давлением |")
            content.append("| Техническое обслуживание | Очки, перчатки, халат | Обесточивание перед вскрытием |")
        elif spec.equipment_type == EquipmentType.SPECTROSCOPY:
            content.append("| Работа с лампами | УФ-защитные очки, перчатки | Избегать прямого УФ-излучения |")
            content.append("| Замена кювет | Защитные очки, перчатки | Осторожность с кварцем |")
        
        content.append("")
        
        # Emergency procedures
        content.append("### Аварийные процедуры\n")
        content.append("#### При разливе реагентов:")
        content.append("1. **Немедленно** уведомить персонал в помещении")
        content.append("2. **Изолировать** источник разлива")
        content.append("3. **Использовать** сорбент для локализации")
        content.append("4. **Проветрить** помещение")
        content.append("5. **Утилизировать** отходы согласно инструкции\n")
        
        content.append("#### При поражении электрическим током:")
        content.append("1. **ОБЕСТОЧИТЬ** оборудование")
        content.append("2. **Вызвать** медицинскую помощь")
        content.append("3. **Оказать** первую помощь")
        content.append("4. **Уведомить** руководство\n")
        
        # Regulatory compliance
        content.append("### Нормативные требования\n")
        content.append("**Применимые стандарты безопасности:**")
        for standard in spec.regulatory_standards:
            content.append(f"- {standard}")
        content.append("")
        
        return "\n".join(content)
        
    def _generate_quality_control(self, spec: EquipmentSpecification, context: Dict[str, Any]) -> str:
        """Generate quality control procedures"""
        
        content = []
        content.append("## Контроль качества\n")
        
        content.append("### Система контроля качества\n")
        content.append("#### Входной контроль")
        content.append("1. **Контроль стандартных образцов**")
        content.append("   - Проверка сертификатов")
        content.append("   - Контроль срока годности") 
        content.append("   - Визуальная оценка состояния\n")
        
        content.append("2. **Контроль реагентов**")
        content.append("   - Квалификация поставщика")
        content.append("   - Сопроводительная документация")
        content.append("   - Маркировка и срок годности\n")
        
        content.append("#### Текущий контроль")
        content.append("3. **Контрольные карты**")
        content.append("   - Ведение контрольных карт для критических параметров")
        content.append("   - Контрольные пределы: среднее ± 2σ (предупреждение), ± 3σ (действие)")
        content.append("   - Анализ трендов и систематических отклонений\n")
        
        content.append("4. **Повторяемость и воспроизводимость**")
        content.append("   - Контроль повторяемости: RSD ≤ 2% для n=6")
        content.append("   - Контроль воспроизводимости: межоператорские сравнения")
        content.append("   - Периодичность: еженедельно\n")
        
        content.append("#### Внешний контроль")
        content.append("5. **Межлабораторные сравнения**")
        content.append("   - Участие в программах взаимосравнений")
        content.append("   - Анализ результатов: Z-score ≤ 2")
        content.append("   - Корректирующие действия при Z-score > 2\n")
        
        content.append("### Критерии приемки результатов\n")
        content.append("| Параметр контроля | Критерий приемки | Действия при несоответствии |")
        content.append("|-------------------|------------------|------------------------------|")
        content.append("| Точность | Отклонение от аттестованного значения ≤ 5% | Повторная калибровка |")
        content.append("| Повторяемость | RSD ≤ 2% | Проверка стабильности условий |")
        content.append("| Холостая проба | < 10% от предела обнаружения | Замена реагентов, очистка |")
        content.append("")
        
        content.append("### Документирование контроля качества\n")
        content.append("**Обязательные записи:**")
        content.append("☐ Результаты анализа контрольных образцов")
        content.append("☐ Контрольные карты с отмеченными трендами")
        content.append("☐ Результаты межлабораторных сравнений") 
        content.append("☐ Корректирующие и предупреждающие действия")
        content.append("☐ Периодические обзоры эффективности системы КК")
        content.append("")
        
        return "\n".join(content)
    
    def _generate_maintenance_procedures(self, spec: EquipmentSpecification, context: Dict[str, Any]) -> str:
        """Generate maintenance procedures"""
        
        content = []
        content.append("## Техническое обслуживание\n")
        
        content.append("### График технического обслуживания\n")
        content.append("| Процедура | Периодичность | Ответственный | Документирование |")
        content.append("|-----------|---------------|---------------|------------------|")
        
        for maint in spec.maintenance_procedures:
            content.append(f"| {maint['task']} | {maint['frequency']} | Оператор/Техник | Журнал ТО |")
        
        content.append("")
        
        # Detailed procedures
        content.append("### Детальные процедуры обслуживания\n")
        for i, maint in enumerate(spec.maintenance_procedures, 1):
            content.append(f"#### {i}. {maint['task']}")
            content.append(f"**Периодичность:** {maint['frequency']}")
            content.append(f"**Процедура:** {maint['procedure']}")
            content.append("**Контроль выполнения:**")
            content.append("☐ Процедура выполнена полностью")
            content.append("☐ Запись внесена в журнал")
            content.append("☐ Дата следующего обслуживания назначена")
            content.append("")
        
        return "\n".join(content)
    
    def _generate_generic_section(self, spec: EquipmentSpecification, section_type: str, context: Dict[str, Any]) -> str:
        """Generate generic professional content for other section types"""
        
        content = []
        content.append(f"## {section_type.replace('_', ' ').title()}\n")
        
        if spec.equipment_type != EquipmentType.GENERIC_ANALYTICAL:
            content.append(f"Специализированный контент для {spec.equipment_type.value}:")
        
        # Add context information if available
        if context.get("parameters"):
            content.append("### Технические параметры из документации")
            for param, values in context["parameters"].items():
                content.append(f"- **{param}:** {', '.join([f'{v['value']} {v['unit']}' for v in values])}")
            content.append("")
        
        content.append("### Профессиональные требования")
        content.append("- Соответствие стандартам качества лаборатории")
        content.append("- Интеграция с системой менеджмента качества")
        content.append("- Документирование всех операций")
        content.append("- Обеспечение прослеживаемости результатов")
        content.append("")
        
        return "\n".join(content)
    
    def get_equipment_database_info(self) -> Dict[str, Any]:
        """Get information about available equipment types and specifications"""
        
        info = {}
        for eq_type, spec in self.equipment_database.items():
            info[eq_type.value] = {
                "common_models": spec.common_models,
                "parameter_count": len(spec.critical_parameters),
                "calibration_procedures": len(spec.calibration_requirements),
                "maintenance_tasks": len(spec.maintenance_procedures),
                "safety_considerations": len(spec.safety_considerations),
                "troubleshooting_issues": len(spec.troubleshooting_guide),
                "regulatory_standards": spec.regulatory_standards
            }
        
        return info