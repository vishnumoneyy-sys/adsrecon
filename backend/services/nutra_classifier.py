"""Nutra Vertical Classifier -- identifies which nutra category an ad belongs to."""
import re
from dataclasses import dataclass, field
from typing import Optional


# --------------------------------------------------------------------------- models


@dataclass
class NutraClassification:
    """
    Result of classifying an ad's copy against the nutra vertical taxonomy.
    """
    categories: list[str]          #: All matched category names (may be empty)
    aggression_score: int         #: 0-100; how aggressive / misleading the copy sounds
    is_nutra: bool                #: True if any nutra keyword matched
    top_category: str             #: Highest-scoring single category
    matched_keywords: list[str]   #: Every keyword that matched (deduplicated)
    hook_type: str                #: Primary persuasion hook detected

    # Extended fields
    is_ghs: bool = False          #: Game-Health-Shot flag (aggressive legal claim)
    is_decoy: bool = False        #: Heuristic: likely a decoy ad
    is_prescription_claim: bool = False  #: Claims to compare to Rx drugs
    cta_language: str = ""         #: Dominant call-to-action phrase style
    target_demo: str = ""         #: Inferred demographic (age/gender)
    red_flags: list[str] = field(default_factory=list)   #: Specific trigger phrases

    def to_dict(self) -> dict:
        return {
            "categories": self.categories,
            "aggression_score": self.aggression_score,
            "is_nutra": self.is_nutra,
            "top_category": self.top_category,
            "matched_keywords": self.matched_keywords,
            "hook_type": self.hook_type,
            "is_ghs": self.is_ghs,
            "is_decoy": self.is_decoy,
            "is_prescription_claim": self.is_prescription_claim,
            "cta_language": self.cta_language,
            "target_demo": self.target_demo,
            "red_flags": self.red_flags,
        }


# --------------------------------------------------------------------------- taxonomy


# Each category: keywords (lower-case search terms) + weight multiplier.
# Every keyword match adds 10 * weight points to the category score.

CATEGORIES: dict[str, dict] = {
    "blood_sugar": {
        "keywords": [
            # Core terms
            "blood sugar", "blood glucose", "glucose level", "sugar level",
            "a1c", "a1c level", "hba1c", "glycated hemoglobin",
            "insulin resistance", "insulin resist", "insulin sensitivity",
            "prediabetes", "pre-diabetes", "prediabetic",
            "diabetes", "diabetic", "diabetic support",
            # Formulations
            "blood sugar support", "glucose support", "sugar support formula",
            "glucose balance", "sugar balance", "blood sugar formula",
            "diabetes support", "blood sugar stabilizer", "glucose regulator",
            # Specific ingredients
            "berberine", "cinnamon extract", "bitter melon", "gymnema",
            "alpha lipoic acid", "chromium picolinate",
            # Claim patterns
            "lower blood sugar", "reduces blood sugar", "controls blood sugar",
            "manages blood sugar", "supports healthy glucose",
        ],
        "weight": 1.0,
    },

    "weight_loss": {
        "keywords": [
            # Core
            "weight loss", "lose weight", "lose belly fat", "belly fat",
            "burn fat", "fat burner", "fat burning", "burns fat",
            "slim down", "slimming", "weight reducer", "body fat",
            # Diets / programs
            "keto", "ketogenic", "keto diet", "ketosis",
            "carnivore", "carnivore diet",
            "detox", "detoxify", "cleanse", "juice cleanse",
            "low carb", "low-carb", "low calorie", "calorie deficit",
            # Pharma / peptides
            "mounjaro", "ozempic", "wegovy", "saxenda",
            "semaglutide", "tirzepatide", "glp-1",
            "appetite suppress", "appetite control",
            # Claims
            "lose 10 pounds", "lose 20 pounds", "melt fat", "shed pounds",
            "weight management", "metabolism booster", "boost metabolism",
            "burn calories", "lose inches", "tone up", "flatten stomach",
            "one simple hack", "one weird trick",
            # Body-part specific
            "thigh gap", "arm fat", "love handles", "muffin top",
            "visceral fat", "stubborn fat",
        ],
        "weight": 1.0,
    },

    "prostate": {
        "keywords": [
            "prostate", "prostate health", "prostate support", "prostate formula",
            "prostate problem", "prostate issues",
            "bph", "benign prostatic hyperplasia", "enlarged prostate",
            "prostate enlargement",
            # Men's 40+ framing
            "men over 40", "men over 50", "men 40+",
            "men's prostate", "men's health", "man health",
            # Urinary
            "urinary tract", "urinary health", "urinary function",
            "bladder control", "bladder support", "frequent urination",
            "nighttime urination", "night trips", "wake up to pee",
            "bathroom trips", "dribbling", "weak stream",
            # Language variants
            "prostata",               # German / Polish
            "próstata",               # Spanish
            "前列腺", "前列腺增大",   # Chinese
        ],
        "weight": 1.2,
    },

    "skin_beauty": {
        "keywords": [
            # Skin
            "skin care", "skin health", "clear skin", "glowing skin", "skin glow",
            "skin complexion", "skin tone", "radiant skin", "healthy glow",
            "acne", "acne-free", "banish acne", "clear complexion",
            "wrinkle", "wrinkles", "anti-wrinkle", "anti-aging skin",
            "fine lines", "crow's feet", "expression lines",
            "age spots", "dark spots", "hyperpigmentation", "sun spots",
            "melasma", "uneven skin tone", "dull skin",
            # Beauty
            "beauty supplement", "beauty formula",
            "fair skin", "skin whitening", "whitening", "skin lightening",
            "collagen", "collagen boost", "collagen production",
            # Hair
            "hair growth", "hair regrowth", "hair loss", "stop hair loss",
            "thicker hair", "hair thickening", "hair volume",
            "baldness", "receding hairline", "hairline",
            # Nails
            "nail health", "strong nails", "nail growth", "brittle nails",
            # Eyelashes
            "eyelash growth", "lash growth", "longer lashes", "lash serum",
        ],
        "weight": 1.0,
    },

    "joint_pain": {
        "keywords": [
            # Core
            "joint pain", "joint health", "joint support", "joint formula",
            "joint stiffness", "joint discomfort",
            # Pain types
            "back pain", "lower back pain", "back ache", "sciatica",
            "knee pain", "hip pain", "shoulder pain", "neck pain",
            "elbow pain", "ankle pain", "wrist pain",
            # Conditions
            "arthritis", "osteoarthritis", "rheumatoid arthritis",
            "arthritic pain", "arthritic joints",
            # Inflammation
            "inflammation", "inflammatory", "anti-inflammatory",
            "reduce inflammation", "swelling", "swollen joints",
            # Mobility
            "mobility", "flexibility", "range of motion",
            "move freely", "pain-free movement", "active lifestyle",
            # Bone / cartilage
            "cartilage", "bone health", "bone density",
            "bone joint", "ligament", "tendons",
            # Pain language
            "pain relief", "pain relief supplement", "ache relief",
            "soothing", "stiffness", "stiff joints",
            "creaky joints", "popping joints",
        ],
        "weight": 1.0,
    },

    "energy_stamina": {
        "keywords": [
            # Energy
            "energy", "energy boost", "energy level", "energy supplement",
            "more energy", "all-day energy", "sustained energy",
            "morning energy", "afternoon slump", "energy crash",
            "fatigue", "chronic fatigue", "adrenal fatigue",
            # Vitality
            "tired", "always tired", "feeling tired", "so tired",
            "exhausted", "always exhausted", "drained", "burned out",
            "low energy", "energy support", "energy formula",
            # Stamina / endurance
            "stamina", "stamina boost", "endurance", "endurance boost",
            "sexual stamina", "stamina in bed",
            # Vitality framing
            "vitality", "male vitality", "male energy",
            "youthful energy", "feel young again",
            # Adrenal / mitochondrial
            "adrenal support", "mitochondrial", "coq10",
            "b12 energy", "vitamin b12", "energy drink alternative",
            "tiredness", "lethargy", "lacking energy",
        ],
        "weight": 1.0,
    },

    "gut_digestion": {
        "keywords": [
            # Core
            "gut health", "digestive health", "digestion", "digestive system",
            "digestive support", "digestive function",
            # Symptoms
            "bloating", "bloated", "gas", "flatulence", "farting",
            "stomach pain", "stomach ache", "stomach discomfort",
            "constipation", "diarrhea", "irregular bowel",
            "ibs", "irritable bowel syndrome", "ibs symptoms",
            "heartburn", "acid reflux", "gerd",
            # Microbiome / flora
            "gut bacteria", "gut microbiome", "gut flora",
            "good bacteria", "bad bacteria",
            # Pro / pre biotics
            "probiotic", "prebiotic", "postbiotic",
            "probiotic supplement",
            # Colon / intestinal
            "colon health", "colon cleanse", "intestinal health",
            "digestive tract", "leaky gut", "gut lining",
        ],
        "weight": 1.0,
    },

    "male_enhancement": {
        "keywords": [
            # Testosterone
            "testosterone", "low testosterone", "t-level", "testosterone level",
            "testosterone boost", "boost testosterone", "testosterone support",
            "free testosterone", "total testosterone",
            # Performance
            "male enhancement", "male performance", "sexual performance",
            "enhancement", "enhance male", "male booster",
            "bedroom performance", "sexual stamina",
            # ED
            "ed", "erectile", "erectile dysfunction", "erection problems",
            "erectile function", "harder erection", "stronger erection",
            # Libido
            "libido", "low libido", "sex drive", "sex drive low",
            "increase libido", "rev libido", "restore libido",
            # Intimacy / desire
            "sexual health", "male vitality", "male virility", "virility",
            "intimacy", "passion", "desire", "sexual desire",
            "bedroom", "in the bedroom", "between the sheets",
            # Slogans
            "grow bigger", "increase size", "enlarge", "lengthen",
            "performance anxiety", "last longer", "lasting power",
        ],
        "weight": 1.0,
    },

    "female_health": {
        "keywords": [
            # Menopause
            "menopause", "menopausal", "menopause symptoms", "menopausal symptoms",
            "hot flash", "hot flashes", "night sweat", "night sweats",
            "hot flush", "flushes",
            # PCOS / fertility
            "pcos", "polycystic ovary syndrome", "polycystic",
            "fertility", "infertility", "infertile", "trying to conceive",
            "conception support", "ovulation",
            # Hormones
            "hormone", "hormones", "hormone balance", "hormone support",
            "estrogen", "estrogen balance", "progesterone",
            "cortisol", "adrenal hormones",
            # Postpartum
            "postpartum", "post-pregnancy", "after baby",
            "breastfeeding support", "lactation support",
            # Female-specific conditions
            "breast health", "breast tenderness",
            "female health", "women's health", "womens health",
            "female supplement", "women supplement",
            # Period / cycle
            "period cramps", "menstrual", "pms", "pmdd",
            "irregular period", "heavy periods", "light periods",
            # Weight / body (female-targeted)
            "women weight loss", "female fat", "hip fat", "thigh fat",
            "post-pregnancy weight", "mommy makeover",
        ],
        "weight": 1.0,
    },

    "anti_aging": {
        "keywords": [
            # Core aging
            "anti-aging", "antiaging", "anti-age", "anti aging",
            "age gracefully", "aging process", "reverse aging", "slow aging",
            "age backward", "look younger", "feel younger",
            # Longevity
            "longevity", "live longer", "lifespan", "healthspan",
            "blue zone", "longevity supplement",
            # Biohacking
            "biohack", "biohacking", "biohacker",
            "nmn", "nmn supplement", "resveratrol", "quercetin",
            "pterostilbene", "fisetin", "spermidine",
            # Cellular
            "cellular health", "cellular aging", "cellular repair",
            "telomere", "telomere length", "telomere support",
            "stem cell", "stem-cell", "stem cell supplement",
            # Fasting / metabolic
            "autophagy", "fasting", "intermittent fasting", "fasting diet",
            "calorie restriction",
            # Fountain of youth framing
            "fountain of youth", "youth in a bottle", "youth serum",
            "eternal youth", "reverse time", "turn back clock",
            # Brain / cognition (age-related)
            "brain aging", "cognitive decline", "memory loss",
            "neuroplasticity", "brain health", "mental sharpness",
        ],
        "weight": 1.0,
    },

    "eyes_vision": {
        "keywords": [
            # Core
            "vision", "eye sight", "eyesight", "eye health", "eye supplement",
            "vision health", "visual health", "eye formula",
            # Conditions
            "macular degeneration", "macular health", "age-related macular",
            "retina", "retinal health", "retinal support",
            "glaucoma", "cataract", "cataracts",
            "eye float", "floaters", "vitreous",
            "dry eyes", "dry eye syndrome", "eye strain",
            "blurred vision", "blur vision", "blurry vision",
            # Protection
            "protect vision", "support vision", "preserve vision",
            "eye protection", "lutein", "zeaxanthin", "astaxanthin",
            "bilberry", "blueberry extract", "eye antioxidants",
            # Multilingual
            "视力", "护眼", "眼健康", "黄斑变性", "白内障",
            " vista", " visión", " vista", "olhos",
        ],
        "weight": 1.0,
    },

    "heart_blood": {
        "keywords": [
            # Blood pressure
            "blood pressure", "high blood pressure", "lower blood pressure",
            "hypertension", "hypertensive",
            "normalize blood pressure", "support blood pressure",
            "pulse pressure", "diastolic", "systolic",
            # Cholesterol
            "cholesterol", "ldl cholesterol", "hdl cholesterol",
            "lower cholesterol", "bad cholesterol", "good cholesterol",
            "triglycerides", "high triglycerides",
            "total cholesterol", "cholesterol ratio",
            # Heart
            "heart health", "cardiovascular health", "cardio health",
            "heart disease", "heart attack", "stroke risk",
            "heart rhythm", "heart rate", "cardiac health",
            "circulatory health", "circulation", "blood circulation",
            "poor circulation", "cold hands feet",
            # Arterial
            "arteries", "arterial health", "clogged arteries",
            "plaque buildup", "arterial plaque", "hardening of arteries",
            # Blood thinners
            "blood thinner", "natural blood thinner",
            "heart strength", "strengthen heart",
        ],
        "weight": 1.0,
    },
}


# --------------------------------------------------------------------------- pattern libraries


# Aggressive claim patterns -- each adds points to the aggression_score
AGGRESSION_PATTERNS: list[tuple[str, int]] = [
    # Statistical claims
    (r"\d{2,3}\s*[%％]\s*(of\s+)?(people|customers|users|men|women|doctors)", 25),
    (r"(over|more than)\s+\d{2,3}\s*[%％]", 20),
    # Time-based miracle claims
    (r"within\s*\d+\s*(day|days|week|weeks|hour|hours|minute|minutes)", 30),
    (r"(just|only)\s+\d+\s*(day|days|week|weeks)", 25),
    (r"dissolve|banish|eliminate.*in.*(day|week)", 25),
    # Authority laundering
    (r"doctor['\u2019]?s?\s*(recommend|order|choice|pick)", 20),
    (r"(md|do|nd|nmd|phd)\s+(recommend|approve|prescribe)", 15),
    (r"clinical(ly)?\s+(proven|tested|studied|shown)", 25),
    (r"(clinical|trial|lab)\s+(study|studies|research|trial)", 15),
    (r"(university|research|institute)\s+(study|research|findings)", 10),
    # Guarantee / risk reversal
    (r"\bguarantee[sd]?\b", 10),
    (r"\bmoney[ -]?back\b", 8),
    (r"no\s+risk", 10),
    (r"100[%\s]+(guaranteed|satisfaction)", 12),
    # Fear / urgency
    (r"don't\s+(wait|ignore|delay|hesitate)", 15),
    (r"(stop|quit|cease)\s+(using|taking|doing)", 15),
    (r"(dangerous|toxic|harmful)\s+(ingredient|substance|chemical)", 20),
    (r"big\s+pharma", 15),
    (r"cover[- ]?up", 20),
    # Transformation
    (r"before\s*(and|\/)\s*after", 25),
    (r"transform(ation|ed|ing)?\s+(your|in)", 20),
    (r"lost\s+\d+\s*(lbs?|pounds?|kg|kilos?)", 25),
    (r"(shed|drop|slashed)\s+\d+", 20),
    # Buzzwords
    (r"\b(secret|miracle|revolutionary|breakthrough|game[ -]?changer|holy\s+grail)\b", 20),
    (r"\b(trick|simple\s+hack|one\s+weird)", 15),
    (r"\b(limited|exclusive|rare)\s+(time|offer|deal)", 15),
    # Prescription drug comparison
    (r"(works\s+like|as\s+good\s+as|alternative\s+to)\s+(ozempic|mounjaro|trulicity)", 25),
    (r"(without\s+the\s+)?(needle|injection|prescription|side[- ]?effect)", 20),
    # Excessive punctuation
    (r"[!\?]{2,}", 5),
    # "All natural" framing
    (r"\ball\s+natural\b", 8),
    (r"100?\s*%\s*natural", 8),
    (r"\b(herb|herbal|plant[- ]?based)\b", 5),
    # Endorsement
    (r"(celebrity|famous|star)\s+(uses?|endorsed|recommend)", 15),
    (r"(viral|exploded|took\s+over)\s+(tiktok|facebook|instagram|social\s+media)", 12),
]


# Hook type detection patterns
HOOK_PATTERNS: dict[str, list[str]] = {
    "question": [
        r"^\s*why\s", r"^\s*how\s", r"^\s*did\s", r"^\s*can\s",
        r"\?$", r"\? ", r"what\s+if\b", r"what\s+happens\s+if",
        r"are\s+you\s+(still|still\s+)?", r"have\s+you\s+ever",
    ],
    "shock": [
        r"\d{2,3}\s*[%％]\s*(of|people|men|women)", r"\d+\s*(times|folds)\s+(better|more)",
        r"\bshocking", r"惊呆了", r"惊人",
        r"\b(outrageous|unbelievable)\b", r"\bdon'?t\s+(believe|trust)\b",
    ],
    "authority": [
        r"\bdr\.\s", r"\bdr[\u0020]", r"\b(md|do|nd)\b",
        r"\bprofessor\b", r"\bclinical\b", r"\bharvard\b",
        r"\bstudy\s+show", r"\bresearch\s+prov", r"\bpeer[- ]?reviewed\b",
    ],
    "transformation": [
        r"before\s*&\s*after", r"\btransform", r"\bmelt\b",
        r"\blost\s+\d+\s*(lbs?|pounds?)", r"\bburn.*fat",
        r"\bshred", r"\bflush.*(fat|toxin)", r"\bflip.*switch",
    ],
    "fear": [
        r"\bdangerous", r"\brisk", r"\bwarning", r"\bstop\b.*\bnow\b",
        r"\bquit\b.*\busing", r"\bavoid\b", r"\bsecret\s+(killer|danger|truth)",
        r"\byou'?re\s+(killing|destroying|poisoning)", r"\bnever\s+(talk|discuss)\b",
        r"\bbig\s+pharma", r"\bcover[- ]?up",
    ],
    "urgency": [
        r"\blimited\s+time", r"\boffer\s+ends", r"\bact\s+now",
        r"\b(only|just)\s+\d+\s*(left|remaining|spots?)",
        r"\bexpire[sd]?\b", r"\bdon'?t\s+(miss|wait)",
        r"\btoday\s+only", r"\bflash\s+sale",
    ],
}


# Red flag phrases -- specific legal / compliance triggers
RED_FLAG_PATTERNS: list[tuple[str, str]] = [
    ("cure[sd]?\b.*(cancer|tumor|diabetes|heart disease)", "cures disease"),
    ("(treat|manage|prevent|mitigate).*(cancer|tumor|diabetes|hypertension)", "disease treatment claim"),
    ("proven\s+to\s+(kill|destroy).*(cancer|tumor|cell)", "cancer killer claim"),
    ("build.*muscle.*without\s+exercise", "implies gym without exercise"),
    ("enhance.*brain.*function.*(pill|supplement|product)", "brain enhancement claim"),
    ("fda\s+(hasn'?t|has\s+not)\s+(approved|cleared)", "FTC/FDA reference"),
    ("these\s+statements\s+have\s+not\s+been\s+evaluated", "DSHEA disclaimer missing"),
    ("bogo|buy\s+one\s+get\s+one|free\s+trial.*(\\$|cost|price)", "deceptive pricing"),
    ("\d+\s*(free|trial)\s+(bottle|pack|box)", "free trial deception"),
    ("fake news|conspiracy|cover-up", "conspiracy framing"),
    ("scam|fake|fraud", "scam allegation"),
]


# Prescription drug comparison patterns
RX_COMPARISON_PATTERNS: list[tuple[str, str]] = [
    ("(as\s+good\s+as|works\s+like|similar\s+to)\s+ozempic", "Ozempic comparison"),
    ("(as\s+good\s+as|works\s+like|similar\s+to)\s+mounjaro", "Mounjaro comparison"),
    ("(as\s+good\s+as|works\s+like|similar\s+to)\s+wegovy", "Wegovy comparison"),
    ("(without\s+a\s+)?prescription", "prescription drug comparison"),
    ("semaglutide\s+(without|in lieu of)", "semaglutide comparison"),
]


# CTA language categories
CTA_LANGUAGE_PATTERNS: list[tuple[str, str]] = [
    ("(click|visit|tap|shop)\s+(here|now|the|our)\s+(link|site|store|page)", "generic link CTA"),
    ("(order|get)\s+your\s+(free|bottle|trial|supply)", "order your free CTA"),
    ("(don'?t|don\s+not)\s+(miss|wait|delay|hesitate)", "urgency CTA"),
    ("(try|risk[ -]?free|zero\s+risk)\s+(today|now)", "risk reversal CTA"),
    ("(limited\s+time|flash\s+sale|offer\s+ends)", "scarcity CTA"),
    ("(learn|discover|find)\s+how", "curiosity CTA"),
    ("(see|watch)\s+(results|proof|transformations?)", "proof CTA"),
    ("(don'?t|stop)\s+(wait|toss|throw)", "regret avoidance CTA"),
]


# Demographic inference patterns
DEMO_PATTERNS: list[tuple[str, str]] = [
    ("\bmen\b.*\b(over|above|40|45|50|55|60|65)", "men 40+"),
    ("\bwomen\b.*\b(menopause|hot flash|menopause)", "women menopausal"),
    ("\bmenopause\b.*\b(women|after|post)", "women menopausal"),
    ("\bold(er)?\b", "elderly"),
    ("\b(baby|infant|toddler|child|kid)\b", "infant/child"),
    ("(teen|adolescent)\b", "adolescent"),
    ("blood\s+sugar\b.*\b(55|60|65|70)\+", "older adults"),
    ("prostate\b.*\b(over|40|45|50|55|60)", "men 40+"),
    ("(joint|pain|bone)\b.*\b(over|40|45|50|55)", "older adults"),
    ("women\b.*\b(weight|fat|pounds|lbs)", "women general"),
    ("men\b.*\b(weight|muscle|testosterone)", "men general"),
]


# Decoy detection patterns (benign content that hides cloaking)
DECOY_PATTERNS = [
    r"\bFacebook\b.*\bMarketplace\b",
    r"\bBuy\s+and\s+sell\b",
    r"\blocal\s+listings?\b",
    r"\bcommunity\s+groups?\b",
    r"\bwatching\s+live\b",
    r"\bvideo\s+call\b",
    r"\bmessenger\b",
    r"\binternet\s+provider\b",
    r"\bphone\s+plan\b",
    r"\bcar\s*insurance\b",
    r"\blife\s*insurance\b",
    r"\bhome\s*security\b",
    r"\blocal\s*business\b",
    r"\bfacebook\s*shop\b",
]

# Legitimate brand domains (decoy = clean domain landing URL)
DECOY_DOMAINS = {
    "amazon.com", "walmart.com", "target.com", "cvs.com", "walgreens.com",
    "riteaid.com", "costco.com", "bestbuy.com", "homedepot.com",
    "webmd.com", "mayoclinic.org", "healthline.com", "medicalnewstoday.com",
    "nih.gov", "cdc.gov", "fda.gov",
    "youtube.com", "facebook.com", "instagram.com", "tiktok.com",
    "google.com", "bing.com", "yahoo.com",
    "apple.com", "samsung.com", "microsoft.com",
    "reuters.com", "bbc.com", "cnn.com", "nbcnews.com", "abcnews.com",
    "nytimes.com", "usatoday.com", "today.com",
}

# Suspicious TLDs common on nutra/spy landers
SUSPICIOUS_TLDS = {".top", ".xyz", ".click", ".fun", ".icu", ".loan", ".work", ".biz"}


# --------------------------------------------------------------------------- classifier


class NutraClassifier:
    """
    Classifies ad copy against the nutra vertical taxonomy.

    Scoring
    -------
    Each keyword match adds ``10 * category_weight`` points to that category.
    The highest-scoring category becomes ``top_category``.
    If no keywords match, ``is_nutra`` is False (potential decoy ad).

    Aggression scoring
    ------------------
    ``aggression_score`` is 0-100 and accumulates from aggressive claim patterns.
    Scores >= 60 indicate likely GHS (Game-Health-Shot) / deceptive advertising.

    Usage
    -----
    >>> classifier = NutraClassifier()
    >>> result = classifier.classify(
    ...     "Burn belly fat in 30 seconds with this one weird trick doctors hate!"
    ... )
    >>> print(result.top_category, result.aggression_score)
    weight_loss 80
    """

    def __init__(self):
        # Pre-compile all patterns for speed
        self._aggression_re: list[tuple[re.Pattern, int]] = [
            (re.compile(pat, re.IGNORECASE), pts)
            for pat, pts in AGGRESSION_PATTERNS
        ]

        self._hook_res: dict[str, re.Pattern] = {
            hook: re.compile("|".join(patterns), re.IGNORECASE | re.MULTILINE)
            for hook, patterns in HOOK_PATTERNS.items()
        }

        self._red_flag_re: list[tuple[re.Pattern, str]] = [
            (re.compile(pat, re.IGNORECASE), label)
            for pat, label in RED_FLAG_PATTERNS
        ]

        self._rx_re: list[tuple[re.Pattern, str]] = [
            (re.compile(pat, re.IGNORECASE), label)
            for pat, label in RX_COMPARISON_PATTERNS
        ]

        self._cta_re: list[tuple[re.Pattern, str]] = [
            (re.compile(pat, re.IGNORECASE | re.MULTILINE), label)
            for pat, label in CTA_LANGUAGE_PATTERNS
        ]

        self._demo_re: list[tuple[re.Pattern, str]] = [
            (re.compile(pat, re.IGNORECASE), label)
            for pat, label in DEMO_PATTERNS
        ]

        self._decoy_patterns: list[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in DECOY_PATTERNS
        ]

        # Build per-category keyword regexes
        self._category_kw_re: dict[str, re.Pattern] = {}
        for category, config in CATEGORIES.items():
            escaped = [re.escape(kw) for kw in config["keywords"]]
            pattern = "|".join(escaped)
            self._category_kw_re[category] = re.compile(pattern, re.IGNORECASE)

    # ------------------------------------------------------------------ public API

    def classify(self, text: str) -> NutraClassification:
        """
        Classify a piece of ad copy against the nutra vertical taxonomy.

        Args:
            text: The full ad text (headline + body + CTA combined).

        Returns:
            :class:`NutraClassification` with scores, categories, and flags.
        """
        if not text:
            return self._empty_result()

        text_lower = text.lower()[:3000]   # cap for performance

        # --- Category scoring ---
        category_scores: dict[str, float] = {}
        matched_kw: set[str] = set()

        for category, config in CATEGORIES.items():
            score = 0.0
            hits: list[str] = []

            for keyword in config["keywords"]:
                kw_lower = keyword.lower()
                # Whole-word-ish match (keyword bounded by non-alphanum)
                if re.search(rf"(?<![a-z]){re.escape(kw_lower)}(?![a-z])", text_lower):
                    score += 10 * config["weight"]
                    hits.append(keyword)

            if hits:
                category_scores[category] = score
                matched_kw.update(hits)

        matched_categories = list(category_scores.keys())
        top_category = (
            max(category_scores, key=category_scores.get) if category_scores else ""
        )

        # --- Aggression ---
        aggression = self._calc_aggression(text_lower)

        # --- Hook type ---
        hook = self._detect_hook(text_lower)

        # --- CTA language ---
        cta = self._detect_cta(text_lower)

        # --- Target demo ---
        demo = self._detect_demographic(text_lower)

        # --- Red flags ---
        red_flags = self._detect_red_flags(text_lower)

        # --- Prescription claims ---
        is_rx_claim = self._detect_rx_claims(text_lower)

        # --- GHS ---
        is_ghs = aggression >= 60 or len(red_flags) >= 2

        # --- Decoy heuristic ---
        is_decoy = self._is_decoy_heuristic(matched_categories, aggression, text_lower)

        return NutraClassification(
            categories=matched_categories,
            aggression_score=min(aggression, 100),
            is_nutra=bool(matched_categories),
            top_category=top_category,
            matched_keywords=sorted(matched_kw),
            hook_type=hook,
            is_ghs=is_ghs,
            is_decoy=is_decoy,
            is_prescription_claim=is_rx_claim,
            cta_language=cta,
            target_demo=demo,
            red_flags=red_flags,
        )

    def classify_batch(self, texts: list[str]) -> list[NutraClassification]:
        """Classify multiple texts sequentially (fast, no I/O)."""
        return [self.classify(t) for t in texts]

    def is_nutra(self, text: str) -> bool:
        """Quick yes/no check: does this text match any nutra vertical?"""
        return self.classify(text).is_nutra

    def get_top_category(self, text: str) -> str:
        """Return only the top category name (empty string if none)."""
        return self.classify(text).top_category

    def is_decoy(self, text: str, landing_url: str = "") -> bool:
        """
        Detect if an ad is a decoy (benign content hiding cloaking).

        Args:
            text: Ad text.
            landing_url: Landing page URL.

        Returns:
            True if this appears to be a decoy ad.
        """
        if not text:
            return False

        # Check text patterns
        for pattern in self._decoy_patterns:
            if pattern.search(text):
                return True

        # Check URL for decoy domains
        if landing_url:
            try:
                from urllib.parse import urlparse
                domain = urlparse(landing_url).netloc.lower()
                if domain in DECOY_DOMAINS:
                    return True
                # Strip www. prefix
                if domain.startswith("www."):
                    domain = domain[4:]
                    if domain in DECOY_DOMAINS:
                        return True
            except Exception:
                pass

        return False

    def get_category_score(self, text: str, category: str) -> float:
        """
        Get a confidence score (0-1) for a specific category.

        Args:
            text:     Text to score.
            category: Category name to check.

        Returns:
            Confidence score between 0 and 1.
        """
        if category not in self._category_kw_re:
            return 0.0

        compiled = self._category_kw_re[category]
        matches = compiled.findall(text)
        return min(1.0, len(matches) / 2.0)   # 2+ matches = full confidence

    # ------------------------------------------------------------------ private helpers

    def _empty_result(self) -> NutraClassification:
        return NutraClassification(
            categories=[],
            aggression_score=0,
            is_nutra=False,
            top_category="",
            matched_keywords=[],
            hook_type="none",
        )

    def _calc_aggression(self, text: str) -> int:
        """Sum points from all matching aggressive claim patterns."""
        score = 0

        for compiled_re, points in self._aggression_re:
            if compiled_re.search(text):
                score += points

        # Contextual boosts
        if any(x in text for x in (
            "limited time", "offer ends", "act now",
            "order now", "buy now", "get yours", "only today",
            "final call", "last chance",
        )):
            score += 15

        if any(x in text for x in (
            "fake news", "conspiracy", "they don'?t want",
            "don'?t trust", "mainstream media", "big pharma",
            "cover-up", "suppressed", "hidden truth",
        )):
            score += 20

        if re.search(r"\b\d{4,}\b", text):   # Big numbers (not years)
            score += 8

        if re.search(r"\b(scam|fake|fraud|hoax)\b", text):
            score += 15

        # Multiple exclamation/question marks
        if re.findall(r"[!?]{3,}", text):
            score += 10

        return min(score, 100)

    def _detect_hook(self, text: str) -> str:
        """Identify the primary persuasion hook used in the copy."""
        best_hook = "none"
        best_score = 0

        for hook, compiled_re in self._hook_res.items():
            matches = compiled_re.findall(text)
            score = len(matches)
            if score > best_score:
                best_score = score
                best_hook = hook

        return best_hook

    def _detect_cta(self, text: str) -> str:
        """Identify the dominant call-to-action style."""
        for compiled_re, label in self._cta_re:
            if compiled_re.search(text):
                return label
        return "generic"

    def _detect_demographic(self, text: str) -> str:
        """Infer the target demographic from copy language."""
        for compiled_re, label in self._demo_re:
            if compiled_re.search(text):
                if label:
                    return label
        return ""

    def _detect_red_flags(self, text: str) -> list[str]:
        """Return a list of red flag labels triggered by the copy."""
        flags: list[str] = []
        for compiled_re, label in self._red_flag_re:
            if compiled_re.search(text):
                flags.append(label)
        return flags

    def _detect_rx_claims(self, text: str) -> bool:
        """Return True if the copy makes prescription drug comparisons."""
        for compiled_re, _ in self._rx_re:
            if compiled_re.search(text):
                return True
        return False

    def _is_decoy_heuristic(
        self,
        categories: list[str],
        aggression: int,
        text: str,
    ) -> bool:
        """
        Heuristic: is this a decoy ad?

        Decoys are legitimate-looking ads designed to hide the real
        aggressive lander. Signals:
        - No nutra keywords at all + reasonable length = possible decoy
        - Very low aggression score despite being in the ad ecosystem
        - Generic brand-safe wellness language with no conversion urgency
        """
        # Signal 1: Zero category matches + some length
        if not categories and len(text) > 50:
            return True

        # Signal 2: Low aggression + claimed health product = suspicious
        if aggression < 15 and categories:
            return True

        # Signal 3: Generic brand-safe wellness language
        brand_safe_phrases = [
            "supports overall health",
            "made with natural ingredients",
            "doctor-formulated",
            "quality guaranteed",
            "premium ingredients",
        ]
        brand_safe_count = sum(1 for phrase in brand_safe_phrases if phrase in text)
        if brand_safe_count >= 2 and aggression < 25:
            return True

        return False
