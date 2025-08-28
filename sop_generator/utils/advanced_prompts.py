from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re
import json


class SectionType(Enum):
    PURPOSE_SCOPE = "purpose_scope"
    RESPONSIBILITY = "responsibility"
    SAFETY_RISK = "safety_risk"  
    EQUIPMENT_MATERIALS = "equipment_materials"
    PROCEDURES = "procedures"
    QUALITY_CONTROL = "quality_control"
    DOCUMENTATION = "documentation"
    REFERENCES = "references"
    TROUBLESHOOTING = "troubleshooting"


class EquipmentCategory(Enum):
    CHROMATOGRAPHY = "chromatography"
    SPECTROSCOPY = "spectroscopy"
    MICROSCOPY = "microscopy"
    ANALYTICAL_BALANCE = "analytical_balance"
    CENTRIFUGE = "centrifuge"
    THERMAL_ANALYZER = "thermal_analyzer"
    GENERIC = "generic"


@dataclass
class PromptTemplate:
    """Professional prompt template with context-aware generation"""
    section_type: SectionType
    equipment_category: EquipmentCategory
    base_prompt: str
    technical_requirements: List[str]
    safety_requirements: List[str]
    regulatory_requirements: List[str]
    quality_criteria: List[str]
    examples: List[str] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []


class AdvancedPromptEngine:
    """Advanced content generation prompt system for professional SOP creation"""
    
    def __init__(self):
        self.prompt_templates = self._initialize_prompt_templates()
        self.context_enhancers = self._initialize_context_enhancers()
        self.validation_criteria = self._initialize_validation_criteria()
    
    def _initialize_prompt_templates(self) -> Dict[SectionType, Dict[EquipmentCategory, PromptTemplate]]:
        """Initialize comprehensive prompt templates for each section type and equipment category"""
        
        templates = {}
        
        # PURPOSE AND SCOPE SECTION
        templates[SectionType.PURPOSE_SCOPE] = {
            EquipmentCategory.CHROMATOGRAPHY: PromptTemplate(
                section_type=SectionType.PURPOSE_SCOPE,
                equipment_category=EquipmentCategory.CHROMATOGRAPHY,
                base_prompt="""
Создай раздел "Цель и область применения" для хроматографической процедуры с указанием:

КОНКРЕТНЫЕ ЦЕЛИ ПРОЦЕДУРЫ:
- Точное определение аналитов с указанием диапазонов концентраций
- Типы образцов и матриц (плазма, моча, почва, пищевые продукты и т.д.)
- Специфические требования к подготовке образцов
- Ожидаемые аналитические характеристики (LOD, LOQ, линейность)

ОБЛАСТЬ ПРИМЕНЕНИЯ:
- Конкретные отрасли и лаборатории
- Регулируемые области (фармацевтика, пищевая, экологическая)
- Соответствие специфическим стандартам (USP, EP, FDA)

ОГРАНИЧЕНИЯ И ИСКЛЮЧЕНИЯ:
- Неприменимые типы образцов
- Ограничения по концентрациям
- Несовместимые матрицы
- Исключения по температуре, pH, растворителям
""",
                technical_requirements=[
                    "Укажите конкретные диапазоны концентраций для каждого аналита",
                    "Определите требования к стабильности образцов",
                    "Укажите критерии приемлемости системы пригодности",
                    "Определите требования к валидации методики"
                ],
                safety_requirements=[
                    "Укажите опасные растворители и их классы",
                    "Определите требования к вытяжной вентиляции",
                    "Укажите необходимые СИЗ для работы с мобильными фазами",
                    "Определите требования к утилизации отходов"
                ],
                regulatory_requirements=[
                    "Ссылка на ICH Q2(R1) валидация аналитических методик",
                    "Соответствие требованиям GMP/GLP",
                    "Соблюдение требований к электронным записям (21 CFR Part 11)"
                ],
                quality_criteria=[
                    "Определены количественные критерии эффективности",
                    "Указаны требования к неопределенности измерений",
                    "Определена прослеживаемость к международным стандартам"
                ]
            ),
            
            EquipmentCategory.SPECTROSCOPY: PromptTemplate(
                section_type=SectionType.PURPOSE_SCOPE,
                equipment_category=EquipmentCategory.SPECTROSCOPY,
                base_prompt="""
Создай раздел "Цель и область применения" для спектроскопической процедуры с указанием:

АНАЛИТИЧЕСКИЕ ЦЕЛИ:
- Качественное и/или количественное определение компонентов
- Спектральные диапазоны и характеристические полосы поглощения
- Требования к разрешению и точности измерений
- Специфические требования к подготовке образцов

ОБЛАСТЬ ПРИМЕНЕНИЯ:
- Типы анализируемых веществ (органические, неорганические)
- Физические формы образцов (растворы, твердые тела, газы)
- Отраслевые применения (фармацевтика, нефтехимия, материаловедение)
- Соответствие международным стандартам (ASTM, ISO)

ОГРАНИЧЕНИЯ И ИСКЛЮЧЕНИЯ:
- Ограничения по оптической плотности
- Несовместимые растворители
- Ограничения по размеру частиц
- Температурные ограничения измерений
""",
                technical_requirements=[
                    "Укажите диапазоны длин волн и спектральное разрешение",
                    "Определите требования к стабильности источников излучения",
                    "Укажите критерии выбора кювет и держателей образцов",
                    "Определите процедуры контроля стрей-света"
                ],
                safety_requirements=[
                    "Укажите меры защиты от УФ и ИК излучения",
                    "Определите требования к работе с токсичными растворителями",
                    "Укажите меры безопасности при работе с лазерными источниками"
                ],
                regulatory_requirements=[
                    "Соответствие USP <857> УФ-видимая спектроскопия",
                    "Соблюдение требований ISO 17025",
                    "Соответствие ГОСТ 8.207-76 для фотометров"
                ],
                quality_criteria=[
                    "Определена воспроизводимость и повторяемость",
                    "Указаны критерии линейности детекторов",
                    "Определены требования к калибровке длин волн"
                ]
            ),
            
            # Add generic template for other equipment types
            EquipmentCategory.GENERIC: PromptTemplate(
                section_type=SectionType.PURPOSE_SCOPE,
                equipment_category=EquipmentCategory.GENERIC,
                base_prompt="""
Создай раздел "Цель и область применения" с профессиональной детализацией:

КОНКРЕТНЫЕ ЦЕЛИ:
- Четкое определение измеряемых параметров
- Диапазоны измерений и требуемая точность
- Типы анализируемых объектов
- Ожидаемые аналитические характеристики

ОБЛАСТЬ ПРИМЕНЕНИЯ:
- Конкретные области использования
- Применимые отрасли и лаборатории
- Соответствие стандартам и нормативам
- Интеграция с существующими системами

ОГРАНИЧЕНИЯ И ИСКЛЮЧЕНИЯ:
- Четко определенные случаи неприменимости
- Ограничения по условиям эксплуатации
- Исключения по типам образцов или материалов
- Особые требования к персоналу
""",
                technical_requirements=[
                    "Определите измеряемые параметры и их диапазоны",
                    "Укажите требования к точности и воспроизводимости",
                    "Определите критерии приемлемости результатов"
                ],
                safety_requirements=[
                    "Определите основные опасности процедуры",
                    "Укажите необходимые меры безопасности",
                    "Определите требования к СИЗ"
                ],
                regulatory_requirements=[
                    "Укажите применимые стандарты и нормативы",
                    "Определите требования к документированию"
                ],
                quality_criteria=[
                    "Определены критерии качества процедуры",
                    "Указаны требования к валидации"
                ]
            )
        }
        
        # SAFETY AND RISK ASSESSMENT SECTION
        templates[SectionType.SAFETY_RISK] = {
            EquipmentCategory.CHROMATOGRAPHY: PromptTemplate(
                section_type=SectionType.SAFETY_RISK,
                equipment_category=EquipmentCategory.CHROMATOGRAPHY,
                base_prompt="""
Создай детальный раздел "Анализ рисков и меры безопасности" для хроматографии:

ИДЕНТИФИКАЦИЯ ОПАСНОСТЕЙ:
1. **Химические риски:**
   - Токсичность мобильных фаз (ацетонитрил класс 1B, метанол класс 1B)
   - Коррозионные свойства буферов (трифторуксусная кислота)
   - Канцерогенные растворители (ДМСО, некоторые галогенированные)
   - Реактивность и несовместимость компонентов

2. **Физические риски:**
   - Высокое давление системы (до 600 бар) - риск разрыва фитингов
   - Температурные опасности (нагреватели колонок до 80°C)
   - Острые предметы (иглы инжекторов, осколки стеклянной посуды)
   - Электрические опасности (высоковольтные детекторы)

3. **Эргономические факторы:**
   - Повторяющиеся движения при подготовке образцов
   - Неправильная посадка при длительной работе
   - Нагрузка на зрение при работе с мелкими деталями

ОЦЕНКА РИСКОВ (матрица 5×5):
- Критические риски (Р×Т ≥ 15): Разрыв под давлением, отравление парами
- Высокие риски (Р×Т = 9-12): Химические ожоги, поражение электротоком  
- Средние риски (Р×Т = 4-8): Порезы, раздражение кожи

МЕРЫ КОНТРОЛЯ (иерархия):
1. Исключение: Замена токсичных растворителей безопасными аналогами
2. Инженерные меры: Автоматические системы сброса давления
3. Административные: Обучение, процедуры ЛОТО
4. СИЗ: Нитриловые перчатки, защитные очки, халаты
""",
                technical_requirements=[
                    "Укажите конкретные значения давления и температуры",
                    "Определите критические точки контроля",
                    "Укажите процедуры аварийного отключения",
                    "Определите требования к системам предохранения"
                ],
                safety_requirements=[
                    "Детализируйте требования к вытяжной вентиляции",
                    "Укажите конкретные СИЗ для каждого типа работ",
                    "Определите процедуры деконтаминации",
                    "Укажите требования к хранению химикатов"
                ],
                regulatory_requirements=[
                    "Соответствие ГОСТ 12.1.005-88 (воздух рабочей зоны)",
                    "Соблюдение СанПиН 1.2.3685-21 (гигиенические нормативы)",
                    "Соответствие требованиям OSHA 1910.1200 (HazCom)",
                    "Соблюдение ISO 45001:2018 (система менеджмента ОТ)"
                ],
                quality_criteria=[
                    "Проведена количественная оценка рисков",
                    "Определены конкретные меры контроля для каждого риска",
                    "Указаны критерии эффективности мер безопасности"
                ]
            ),
            
            # Add generic safety template
            EquipmentCategory.GENERIC: PromptTemplate(
                section_type=SectionType.SAFETY_RISK,
                equipment_category=EquipmentCategory.GENERIC,
                base_prompt="""
Создай комплексный раздел "Анализ рисков и меры безопасности":

СИСТЕМАТИЧЕСКАЯ ИДЕНТИФИКАЦИЯ ОПАСНОСТЕЙ:
1. Физические риски (механические, термические, электрические)
2. Химические опасности (токсичность, коррозия, реактивность)
3. Биологические риски (инфекции, аллергены)
4. Эргономические факторы (нагрузки, повторяющиеся движения)
5. Экологические аспекты (выбросы, отходы)

КОЛИЧЕСТВЕННАЯ ОЦЕНКА РИСКОВ:
- Матрица "вероятность × тяжесть последствий"
- Числовые рейтинги рисков
- Приоритизация мер контроля

ИЕРАРХИЯ МЕР КОНТРОЛЯ:
1. Исключение опасности
2. Замена на безопасные альтернативы
3. Инженерные средства защиты
4. Административные меры
5. Средства индивидуальной защиты

ИНТЕГРАЦИЯ В ПРОЦЕДУРЫ:
- Предупреждения в критических точках
- Проверочные листы безопасности
- Процедуры реагирования на инциденты
""",
                technical_requirements=[
                    "Определите технические меры безопасности",
                    "Укажите критические параметры контроля",
                    "Определите системы сигнализации и блокировок"
                ],
                safety_requirements=[
                    "Детализируйте требования к СИЗ",
                    "Укажите процедуры безопасной работы",
                    "Определите аварийные процедуры"
                ],
                regulatory_requirements=[
                    "Соответствие применимым стандартам безопасности",
                    "Соблюдение требований охраны труда",
                    "Соответствие экологическим нормам"
                ],
                quality_criteria=[
                    "Проведен систематический анализ рисков",
                    "Определены эффективные меры контроля",
                    "Указаны критерии мониторинга безопасности"
                ]
            )
        }
        
        # PROCEDURES SECTION
        templates[SectionType.PROCEDURES] = {
            EquipmentCategory.CHROMATOGRAPHY: PromptTemplate(
                section_type=SectionType.PROCEDURES,
                equipment_category=EquipmentCategory.CHROMATOGRAPHY,
                base_prompt="""
Создай детальный раздел "Пошаговые процедуры" для хроматографического анализа:

I. ПОДГОТОВКА СИСТЕМЫ
1. **Проверка готовности оборудования (5-10 мин)**
   - Визуальная инспекция: отсутствие протечек, повреждений ✓
   - Проверка давления в покое: ≤ 5 бар ✓
   - Состояние колонки: давление обратной промывки < 50 бар ✓
   - **Критерий приемки**: Все проверки пройдены, система готова к работе
   - **При отклонении**: См. раздел "Устранение неисправностей"

2. **Подготовка мобильной фазы (15-20 мин)**
   - Взвешивание буферных компонентов: точность ±0.1 мг ✓
   - Растворение в деионизованной воде (удельное сопротивление ≥ 18.2 МОм·см) ✓
   - Доведение pH до 3.0 ± 0.1 (pH-метр калибровка в день измерения) ✓
   - Фильтрация через мембрану 0.22 мкм ✓
   - Дегазация в ультразвуковой бане 10 ± 2 мин ✓
   - **Критерий приемки**: pH в диапазоне, отсутствие пузырьков
   - **ВНИМАНИЕ**: Работа с кислотами - обязательны защитные очки и нитриловые перчатки

3. **Промывка системы и уравновешивание (20-30 мин)**
   - Скорость потока: 1.0 мл/мин ± 2% ✓
   - Состав: 100% буфер А ✓
   - Продолжительность: до стабилизации базовой линии ✓
   - Контроль давления: должно стабилизироваться в пределах 150-200 бар ✓
   - **Критерий приемки**: Дрейф базовой линии < 1 мAU/час
   - **При превышении времени**: Проверить засорение фритов колонки

II. АНАЛИЗ ОБРАЗЦОВ
4. **Инъекция стандартных растворов**
   - Объем инъекции: 10 ± 0.1 мкл ✓
   - Последовательность: бланк → холостая → стандарты по возрастанию ✓
   - Интервал между инъекциями: 15 ± 2 мин ✓
   - **Контроль системы пригодности**:
     * Время удерживания основного пика: 8.5 ± 0.2 мин
     * Количество теоретических тарелок: ≥ 5000
     * Коэффициент асимметрии: 0.8 - 1.5
     * RSD площадей повторных инъекций: ≤ 2.0%
   - **Критерий приемки**: Все параметры в норме
   - **При несоответствии**: Повторная подготовка стандартов или техобслуживание

5. **Анализ тестовых образцов**
   - Предварительная очистка образцов согласно процедуре пробоподготовки ✓
   - Инъекция в том же режиме что и стандарты ✓
   - Контрольные инъекции стандарта каждые 10 образцов ✓
   - **Мониторинг в процессе анализа**:
     * Давление системы: не должно превышать исходное более чем на 20%
     * Время удерживания: дрейф ≤ 2% от исходного
     * Форма пика: отсутствие расщепления или деформации
   - **При отклонениях**: Остановка анализа, диагностика

III. ЗАВЕРШЕНИЕ РАБОТЫ
6. **Промывка и консервация (15-20 мин)**
   - Промывка растворителем совместимым с колонкой: 100% метанол ✓
   - Скорость потока: 0.5 мл/мин ✓
   - Объем промывки: 20 объемов колонки ✓
   - Снижение скорости потока до 0.1 мл/мин перед отключением ✓
   - **Критерий завершения**: Стабильная базовая линия в режиме консервации
""",
                technical_requirements=[
                    "Все параметры должны иметь числовые значения с допусками",
                    "Каждый шаг должен содержать критерии успешного выполнения",
                    "Указаны временные рамки для каждой операции",
                    "Определены действия при отклонениях от нормы"
                ],
                safety_requirements=[
                    "Интегрированы предупреждения в критических точках",
                    "Указаны конкретные СИЗ для каждого этапа",
                    "Определены действия при аварийных ситуациях"
                ],
                regulatory_requirements=[
                    "Соответствие USP <621> Хроматография",
                    "Соблюдение принципов GMP",
                    "Требования к электронным записям"
                ],
                quality_criteria=[
                    "Все процедуры валидированы и документированы",
                    "Определены критерии системы пригодности",
                    "Установлены процедуры контроля качества"
                ]
            )
        }
        
        # TROUBLESHOOTING SECTION  
        templates[SectionType.TROUBLESHOOTING] = {
            EquipmentCategory.GENERIC: PromptTemplate(
                section_type=SectionType.TROUBLESHOOTING,
                equipment_category=EquipmentCategory.GENERIC,
                base_prompt="""
Создай детальный раздел "Устранение неисправностей и диагностика":

ДИАГНОСТИЧЕСКИЙ АЛГОРИТМ:
1. **Первичная диагностика (2-5 мин)**
   - Проверка индикаторов состояния системы
   - Анализ сообщений об ошибках
   - Визуальная инспекция критических компонентов

2. **Систематическая диагностика**
   - Проверка по принципу "от простого к сложному"
   - Изоляция проблемных компонентов
   - Проверка взаимосвязей между системами

ТИПИЧНЫЕ НЕИСПРАВНОСТИ И РЕШЕНИЯ:

**ПРОБЛЕМА 1: [Конкретная проблема]**
📋 **Симптомы:**
- Специфические наблюдаемые признаки
- Изменения в показаниях приборов
- Аномальные звуки, запахи, внешний вид

🔍 **Возможные причины (по приоритету):**
1. Наиболее вероятная причина
2. Вторая по вероятности причина  
3. Редкие, но возможные причины

⚡ **Пошаговое устранение:**
1. **Немедленные действия** (безопасность):
   - Действия для обеспечения безопасности
   - Изоляция опасности
   
2. **Диагностические проверки:**
   - Конкретные измерения и тесты
   - Ожидаемые результаты
   - Критерии оценки
   
3. **Корректирующие действия:**
   - Пошаговые инструкции по устранению
   - Требуемые инструменты и материалы
   - Критерии успешного устранения
   
4. **Проверка эффективности:**
   - Тесты для подтверждения устранения
   - Критерии приемки
   - Действия при неуспешном устранении

🎯 **Критерии успешного устранения:**
- Конкретные измеримые показатели
- Возврат к нормальным параметрам
- Отсутствие повторения проблемы

⚠️ **Когда обращаться к специалисту:**
- Превышение времени диагностики (X минут)
- Необходимость специального оборудования
- Проблемы безопасности

ПРЕВЕНТИВНЫЕ МЕРЫ:
- Регулярные проверки для предотвращения
- Индикаторы раннего предупреждения
- Рекомендации по техобслуживанию

ДОКУМЕНТИРОВАНИЕ:
- Обязательные записи о неисправностях
- Время простоя и влияние на производство
- Эффективность принятых мер
""",
                technical_requirements=[
                    "Систематическая структура диагностики",
                    "Конкретные измерения и критерии",
                    "Четкие алгоритмы принятия решений",
                    "Специфические инструменты и материалы"
                ],
                safety_requirements=[
                    "Приоритет безопасности при диагностике",
                    "Процедуры изоляции опасностей", 
                    "Требования к СИЗ при ремонте"
                ],
                regulatory_requirements=[
                    "Документирование отклонений",
                    "Процедуры уведомления",
                    "Требования к квалификации персонала"
                ],
                quality_criteria=[
                    "Эффективность решений измерима",
                    "Прослеживаемость всех действий",
                    "Анализ корневых причин"
                ]
            )
        }
        
        return templates
    
    def _initialize_context_enhancers(self) -> Dict[str, Any]:
        """Initialize context enhancement patterns"""
        return {
            "technical_detail_enhancers": {
                "parameters": [
                    "Укажите конкретные числовые значения с единицами измерения",
                    "Определите допустимые диапазоны и допуски",
                    "Включите критерии приемки для каждого параметра",
                    "Укажите методы измерения и контроля"
                ],
                "procedures": [
                    "Разбейте на четкие пронумерованные шаги",
                    "Укажите время выполнения для каждого этапа",
                    "Определите критерии успешного выполнения",
                    "Включите действия при отклонениях"
                ],
                "specifications": [
                    "Укажите модели и серийные номера оборудования",
                    "Включите технические характеристики",
                    "Определите требования к калибровке",
                    "Укажите требования к техобслуживанию"
                ]
            },
            "safety_enhancers": [
                "Интегрируйте предупреждения непосредственно в процедурные шаги",
                "Укажите конкретные СИЗ для каждого типа операций",
                "Включите процедуры ЛОТО где применимо", 
                "Определите аварийные процедуры и контакты"
            ],
            "regulatory_enhancers": [
                "Укажите конкретные номера стандартов и разделов",
                "Включите требования к документированию",
                "Определите процедуры валидации",
                "Укажите требования к обучению персонала"
            ]
        }
    
    def _initialize_validation_criteria(self) -> Dict[str, List[str]]:
        """Initialize validation criteria for generated content"""
        return {
            "technical_completeness": [
                "Все параметры имеют числовые значения",
                "Указаны единицы измерения",
                "Определены критерии приемки",
                "Включены процедуры контроля"
            ],
            "safety_integration": [
                "Предупреждения интегрированы в процедуры", 
                "Указаны конкретные СИЗ",
                "Определены аварийные процедуры",
                "Включены ссылки на стандарты безопасности"
            ],
            "regulatory_compliance": [
                "Ссылки на применимые стандарты",
                "Требования к документированию",
                "Процедуры валидации",
                "Требования к квалификации"
            ],
            "operational_readiness": [
                "Процедуры готовы к использованию",
                "Критерии успеха определены",
                "Действия при отклонениях указаны",
                "Временные рамки определены"
            ]
        }
    
    def generate_advanced_prompt(self, 
                                section_type: SectionType,
                                equipment_category: EquipmentCategory = EquipmentCategory.GENERIC,
                                custom_requirements: List[str] = None,
                                reference_context: str = None,
                                previous_content: str = None) -> str:
        """Generate advanced, context-aware prompt for specific section"""
        
        # Get base template
        if section_type in self.prompt_templates:
            if equipment_category in self.prompt_templates[section_type]:
                template = self.prompt_templates[section_type][equipment_category]
            else:
                # Fallback to generic if specific equipment category not found
                template = self.prompt_templates[section_type].get(
                    EquipmentCategory.GENERIC,
                    self.prompt_templates[section_type][list(self.prompt_templates[section_type].keys())[0]]
                )
        else:
            # Create minimal template if section type not found
            template = PromptTemplate(
                section_type=section_type,
                equipment_category=equipment_category,
                base_prompt=f"Создай профессиональный раздел '{section_type.value}' с максимальной детализацией.",
                technical_requirements=["Включите технические детали"],
                safety_requirements=["Включите меры безопасности"],
                regulatory_requirements=["Включите нормативные требования"],
                quality_criteria=["Обеспечьте качество содержания"]
            )
        
        # Build enhanced prompt
        prompt_parts = []
        
        # Base prompt
        prompt_parts.append(template.base_prompt)
        
        # Context integration
        if reference_context:
            prompt_parts.append(f"\n**КОНТЕКСТ ИЗ СПРАВОЧНЫХ ДОКУМЕНТОВ:**\n{reference_context[:1000]}...")
        
        if previous_content:
            prompt_parts.append(f"\n**СВЯЗЬ С ПРЕДЫДУЩИМИ РАЗДЕЛАМИ:**\nОбеспечьте согласованность с: {previous_content[:500]}...")
        
        # Technical requirements
        prompt_parts.append("\n**ОБЯЗАТЕЛЬНЫЕ ТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ:**")
        for req in template.technical_requirements:
            prompt_parts.append(f"✓ {req}")
        
        # Safety requirements
        prompt_parts.append("\n**ТРЕБОВАНИЯ БЕЗОПАСНОСТИ:**")
        for req in template.safety_requirements:
            prompt_parts.append(f"🛡️ {req}")
        
        # Regulatory requirements
        prompt_parts.append("\n**НОРМАТИВНЫЕ ТРЕБОВАНИЯ:**")
        for req in template.regulatory_requirements:
            prompt_parts.append(f"📋 {req}")
        
        # Quality criteria
        prompt_parts.append("\n**КРИТЕРИИ КАЧЕСТВА:**")
        for criteria in template.quality_criteria:
            prompt_parts.append(f"🎯 {criteria}")
        
        # Custom requirements
        if custom_requirements:
            prompt_parts.append("\n**ДОПОЛНИТЕЛЬНЫЕ ТРЕБОВАНИЯ:**")
            for req in custom_requirements:
                prompt_parts.append(f"⭐ {req}")
        
        # Professional standards
        prompt_parts.append("\n**ПРОФЕССИОНАЛЬНЫЕ СТАНДАРТЫ:**")
        prompt_parts.append("• Документ должен быть готов к немедленному производственному использованию")
        prompt_parts.append("• Все инструкции должны быть конкретными и измеримыми")
        prompt_parts.append("• Обеспечьте полную прослеживаемость и документированность")
        prompt_parts.append("• Интегрируйте меры безопасности в каждый этап процедуры")
        
        # Output formatting requirements
        prompt_parts.append("\n**ТРЕБОВАНИЯ К ФОРМАТУ:**")
        prompt_parts.append("• Используйте четкую иерархическую структуру с нумерацией")
        prompt_parts.append("• Создавайте таблицы для технических параметров")
        prompt_parts.append("• Выделяйте предупреждения **ВНИМАНИЕ** и **ПРЕДУПРЕЖДЕНИЕ**")
        prompt_parts.append("• Используйте чекбоксы ☐ для проверочных листов")
        prompt_parts.append("• Включайте конкретные ссылки на стандарты")
        
        return "\n".join(prompt_parts)
    
    def generate_section_specific_prompts(self, 
                                        equipment_type: str,
                                        section_configs: List[Dict[str, Any]],
                                        reference_context: Optional[str] = None) -> List[Dict[str, str]]:
        """Generate section-specific prompts for entire SOP structure"""
        
        # Map equipment type to category
        equipment_category = self._map_equipment_type(equipment_type)
        
        enhanced_prompts = []
        previous_content_summary = ""
        
        for i, section_config in enumerate(section_configs):
            section_title = section_config.get("title", "")
            section_mode = section_config.get("mode", "ai")
            custom_prompt = section_config.get("prompt", "")
            
            # Skip manual sections
            if section_mode == "manual":
                enhanced_prompts.append({
                    "title": section_title,
                    "prompt": "Manual content - no AI generation needed",
                    "mode": "manual"
                })
                continue
            
            # Determine section type
            section_type = self._map_section_title_to_type(section_title)
            
            # Build custom requirements from user prompt
            custom_requirements = []
            if custom_prompt:
                custom_requirements.append(custom_prompt)
            
            # Generate advanced prompt
            advanced_prompt = self.generate_advanced_prompt(
                section_type=section_type,
                equipment_category=equipment_category,
                custom_requirements=custom_requirements,
                reference_context=reference_context,
                previous_content=previous_content_summary if i > 0 else None
            )
            
            enhanced_prompts.append({
                "title": section_title,
                "prompt": advanced_prompt,
                "mode": section_mode,
                "section_type": section_type.value,
                "equipment_category": equipment_category.value
            })
            
            # Update previous content summary for context continuity
            previous_content_summary += f" {section_title};"
        
        return enhanced_prompts
    
    def _map_equipment_type(self, equipment_type: str) -> EquipmentCategory:
        """Map equipment type string to category enum"""
        equipment_type_lower = equipment_type.lower()
        
        if any(keyword in equipment_type_lower for keyword in ['хроматограф', 'chromatograph', 'hplc', 'gc', 'lc-ms']):
            return EquipmentCategory.CHROMATOGRAPHY
        elif any(keyword in equipment_type_lower for keyword in ['спектрометр', 'spectrometer', 'спектрофотометр']):
            return EquipmentCategory.SPECTROSCOPY
        elif any(keyword in equipment_type_lower for keyword in ['микроскоп', 'microscope']):
            return EquipmentCategory.MICROSCOPY
        elif any(keyword in equipment_type_lower for keyword in ['весы', 'balance']):
            return EquipmentCategory.ANALYTICAL_BALANCE
        elif any(keyword in equipment_type_lower for keyword in ['центрифуг', 'centrifuge']):
            return EquipmentCategory.CENTRIFUGE
        elif any(keyword in equipment_type_lower for keyword in ['термоанализ', 'thermal', 'dsc', 'tga']):
            return EquipmentCategory.THERMAL_ANALYZER
        else:
            return EquipmentCategory.GENERIC
    
    def _map_section_title_to_type(self, title: str) -> SectionType:
        """Map section title to section type enum"""
        title_lower = title.lower()
        
        if any(keyword in title_lower for keyword in ['цель', 'назначение', 'область', 'применение', 'purpose', 'scope']):
            return SectionType.PURPOSE_SCOPE
        elif any(keyword in title_lower for keyword in ['ответственность', 'персонал', 'обучение', 'responsibility']):
            return SectionType.RESPONSIBILITY
        elif any(keyword in title_lower for keyword in ['безопасность', 'риск', 'опасность', 'safety', 'risk']):
            return SectionType.SAFETY_RISK
        elif any(keyword in title_lower for keyword in ['оборудование', 'материалы', 'средства', 'equipment', 'materials']):
            return SectionType.EQUIPMENT_MATERIALS
        elif any(keyword in title_lower for keyword in ['процедура', 'методика', 'порядок', 'procedure', 'method']):
            return SectionType.PROCEDURES
        elif any(keyword in title_lower for keyword in ['качество', 'контроль', 'quality', 'control']):
            return SectionType.QUALITY_CONTROL
        elif any(keyword in title_lower for keyword in ['документ', 'запись', 'documentation', 'records']):
            return SectionType.DOCUMENTATION
        elif any(keyword in title_lower for keyword in ['ссылки', 'стандарт', 'норматив', 'references', 'standards']):
            return SectionType.REFERENCES
        elif any(keyword in title_lower for keyword in ['неисправность', 'проблема', 'диагностика', 'troubleshooting']):
            return SectionType.TROUBLESHOOTING
        else:
            return SectionType.PROCEDURES  # Default to procedures
    
    def validate_generated_content(self, content: str, section_type: SectionType) -> Dict[str, Any]:
        """Validate generated content against professional criteria"""
        
        validation_results = {
            "overall_score": 0,
            "technical_completeness": 0,
            "safety_integration": 0, 
            "regulatory_compliance": 0,
            "operational_readiness": 0,
            "issues": [],
            "recommendations": []
        }
        
        # Get validation criteria for section type
        if section_type.value in self.validation_criteria:
            criteria = self.validation_criteria[section_type.value]
        else:
            # Use general criteria
            criteria = self.validation_criteria["operational_readiness"]
        
        # Technical completeness check
        tech_score = 0
        if re.search(r'\d+(?:\.\d+)?\s*[a-zA-Zа-яА-Я%℃°]', content):  # Numbers with units
            tech_score += 25
        if re.search(r'критери[йя]|приемк[аи]|допуск', content, re.IGNORECASE):  # Acceptance criteria
            tech_score += 25
        if re.search(r'диапазон|предел|от\s+\d+\s+до\s+\d+', content, re.IGNORECASE):  # Ranges
            tech_score += 25
        if re.search(r'контроль|измерени|проверк', content, re.IGNORECASE):  # Control procedures
            tech_score += 25
        
        validation_results["technical_completeness"] = tech_score
        
        # Safety integration check
        safety_score = 0
        if re.search(r'\*\*(?:ВНИМАНИЕ|ПРЕДУПРЕЖДЕНИЕ)\*\*', content):  # Safety warnings
            safety_score += 30
        if re.search(r'сиз|защитн.*средств|перчатк|очк', content, re.IGNORECASE):  # PPE
            safety_score += 30
        if re.search(r'аварийн|экстренн|чрезвычайн', content, re.IGNORECASE):  # Emergency procedures
            safety_score += 20
        if re.search(r'гост|санпин|iso|osha', content, re.IGNORECASE):  # Safety standards
            safety_score += 20
        
        validation_results["safety_integration"] = safety_score
        
        # Regulatory compliance check
        reg_score = 0
        if re.search(r'(?:ГОСТ|ISO|OSHA|USP|ICH)\s+[\d.-]+', content):  # Standard references
            reg_score += 40
        if re.search(r'документ.*требовани|запис.*ведени', content, re.IGNORECASE):  # Documentation
            reg_score += 30
        if re.search(r'валидаци|поверк|калибровк', content, re.IGNORECASE):  # Validation
            reg_score += 30
        
        validation_results["regulatory_compliance"] = reg_score
        
        # Operational readiness check
        op_score = 0
        if re.search(r'^\d+\.\s+', content, re.MULTILINE):  # Numbered steps
            op_score += 25
        if re.search(r'время.*мин|продолжительност', content, re.IGNORECASE):  # Time requirements
            op_score += 25
        if re.search(r'при\s+(?:отклонени|несоответстви|превышени)', content, re.IGNORECASE):  # Exception handling
            op_score += 25
        if len(content) > 500:  # Sufficient detail
            op_score += 25
        
        validation_results["operational_readiness"] = op_score
        
        # Calculate overall score
        validation_results["overall_score"] = int((tech_score + safety_score + reg_score + op_score) / 4)
        
        # Generate recommendations
        if tech_score < 75:
            validation_results["recommendations"].append("Добавить больше технических деталей с конкретными параметрами")
        if safety_score < 75:
            validation_results["recommendations"].append("Усилить интеграцию мер безопасности")
        if reg_score < 75:
            validation_results["recommendations"].append("Добавить ссылки на нормативные документы")
        if op_score < 75:
            validation_results["recommendations"].append("Улучшить операционную готовность процедур")
        
        return validation_results
    
    def get_equipment_specific_enhancements(self, equipment_category: EquipmentCategory) -> Dict[str, Any]:
        """Get equipment-specific enhancements and templates"""
        
        enhancements = {
            "common_parameters": [],
            "typical_procedures": [],
            "safety_considerations": [],
            "regulatory_standards": [],
            "troubleshooting_patterns": []
        }
        
        if equipment_category == EquipmentCategory.CHROMATOGRAPHY:
            enhancements.update({
                "common_parameters": [
                    "Скорость потока (мл/мин)", "Температура колонки (°C)",
                    "Давление системы (бар)", "Объем инъекции (мкл)",
                    "Время удерживания (мин)", "Разрешение пиков"
                ],
                "typical_procedures": [
                    "Подготовка мобильной фазы", "Уравновешивание системы",
                    "Система пригодности", "Последовательность анализа",
                    "Промывка и консервация"
                ],
                "safety_considerations": [
                    "Токсичные растворители", "Высокое давление",
                    "Кислотные буферы", "Утилизация отходов"
                ],
                "regulatory_standards": [
                    "USP <621> Chromatography", "ICH Q2(R1)",
                    "ГОСТ 31640-2012", "ISO 17025:2017"
                ]
            })
        elif equipment_category == EquipmentCategory.SPECTROSCOPY:
            enhancements.update({
                "common_parameters": [
                    "Длина волны (нм)", "Спектральная ширина щели (нм)",
                    "Абсорбция (A)", "Интенсивность излучения",
                    "Время интегрирования (с)"
                ],
                "typical_procedures": [
                    "Проверка длины волны", "Калибровка абсорбции",
                    "Контроль стрей-света", "Подготовка образцов"
                ],
                "safety_considerations": [
                    "УФ излучение", "Кварцевые компоненты",
                    "Токсичные растворители", "Высокая температура ламп"
                ]
            })
        
        return enhancements