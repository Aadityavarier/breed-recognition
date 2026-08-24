import os
import sys
import time
import hashlib
from flask import Flask, request, jsonify, send_file, render_template_string

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(BASE_DIR, "expert-dashboard")
TEMPLATE_PATH = os.path.join(DASHBOARD_DIR, "templates", "index.html")

app = Flask(__name__)

# Mock 1x1 transparent/colored base64 image placeholders for Grad-CAM fallback
GRAD_CAM_ORIGINAL = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
GRAD_CAM_HEATMAP  = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

class MockEngine:
    name         = "TFLite INT8 Edge Engine"
    version      = "v2.14"
    status       = "Active"
    quantization = "INT8"

# ─────────────────────────────────────────────────────────────────────────────
# COMPREHENSIVE BREED PROFILE DATABASE
# Covers all 15 breeds the inference engine can return.
# Each entry includes:
#   morphological_features  – cranial, horn, dewlap, coat, body
#   explanation_sentence    – plain-language XAI summary
#   specialities            – milk yield, temperament, purpose, disease resistance
#   native_tract            – region / state
#   crossbreeding_partners  – paired breeds for yield improvement
# ─────────────────────────────────────────────────────────────────────────────
BREED_PROFILES = {
    "Gir Cattle": {
        "category": "Indigenous Milch Cattle",
        "native_tract": "Saurashtra (Gir Forest), Gujarat",
        "native_states": ["Gujarat"],
        "avg_milk_yield": "2,000 – 3,200 kg / lactation",
        "speciality": "Highest milk yield among Indian zebu; A2 β-casein milk; heat-tolerant; exported to Brazil and Israel.",
        "temperament": "Docile, manageable",
        "purpose": "Milch",
        "disease_resistance": "High tick resistance; heat-adapted for tropical climate",
        "optimal_crossbreeding": "Jersey × Gir gives 12–15 litres/day; HF × Gir retains A2 milk with improved yield.",
        "crossbreeding_partners": [
            {"breed": "Jersey", "benefit": "Doubles daily yield to 12–15 L while retaining heat tolerance"},
            {"breed": "Holstein Friesian", "benefit": "Increases lactation yield; offspring retain A2 milk trait"},
            {"breed": "Sahiwal", "benefit": "Strengthens tick resistance; suits humid Punjab climate"}
        ],
        "morphological_features": {
            "cranial_structure": "Prominent convex (Roman) forehead — the AI's primary classification signal",
            "horn_curvature": "Half-moon pendulous, curving up and back",
            "dewlap": "Large, pendulous, deeply folded",
            "ears": "Long, pendulous, folded like a leaf — drooping below jaw",
            "coat": "Reddish-brown to white with dark spots; smooth short hair",
            "body": "Medium-large; deep chest; prominent hump"
        },
        "explanation_sentence": "This animal's prominently convex (Roman) forehead and long leaf-shaped pendulous ears are the defining hallmarks of Gir cattle — the AI's attention heatmap shows strong activation on the head and ear region, confirming these morphological cues drove the classification.",
        "data_status": "curated"
    },
    "Sahiwal": {
        "category": "Indigenous Milch Cattle",
        "native_tract": "Montgomery district, Punjab (now Pakistan); Rajasthan/UP in India",
        "native_states": ["Punjab", "Rajasthan", "Uttar Pradesh"],
        "avg_milk_yield": "2,500 – 3,200 kg / lactation",
        "speciality": "India's premier dairy zebu; tick-resistant; heat-tolerant; moderate fat content (4.5%).",
        "temperament": "Extremely docile and calm",
        "purpose": "Milch",
        "disease_resistance": "Excellent tick resistance; moderate trypanosomiasis resistance",
        "optimal_crossbreeding": "HF × Sahiwal is the national recommended cross for tropical dairy.",
        "crossbreeding_partners": [
            {"breed": "Holstein Friesian", "benefit": "National recommended cross for tropical dairy; 15–18 L/day"},
            {"breed": "Jersey", "benefit": "Improves butterfat percentage; suits hill regions"},
            {"breed": "Gir", "benefit": "Enhances disease resistance and A2 milk trait"}
        ],
        "morphological_features": {
            "cranial_structure": "Broad, flat or slightly domed forehead — key differentiator from Gir",
            "horn_curvature": "Short, thick, laterally curved — outward then slightly upward",
            "dewlap": "Moderately pendulous",
            "ears": "Medium-length; horizontal, slightly drooping",
            "coat": "Reddish-brown to dark brown; smooth; loose skin folds",
            "body": "Medium-large; well-muscled; deep barrel"
        },
        "explanation_sentence": "The AI identified this as Sahiwal based on the characteristic flat forehead, thick laterally-curved horns, and reddish-brown loose skin — the heatmap shows attention concentrated on the poll and barrel area, distinguishing it from the convex-headed Gir.",
        "data_status": "curated"
    },
    "Murrah": {
        "category": "Indigenous Buffalo",
        "native_tract": "Rohtak, Hisar, Jind districts of Haryana",
        "native_states": ["Haryana", "Punjab", "Delhi"],
        "avg_milk_yield": "2,200 – 3,500 kg / lactation (7–8% fat)",
        "speciality": "World's highest-yielding buffalo breed; milk fat >7% — critical for ghee and paneer industry.",
        "temperament": "Calm but requires experienced handlers",
        "purpose": "Milch Buffalo",
        "disease_resistance": "Moderate; susceptible to foot-and-mouth; good in humid plains",
        "optimal_crossbreeding": "Murrah × Surti improves adaptability in Gujarat climate.",
        "crossbreeding_partners": [
            {"breed": "Surti", "benefit": "Improves heat tolerance and coastal adaptability"},
            {"breed": "Nili-Ravi", "benefit": "Increases lactation yield in Punjab conditions"},
            {"breed": "Bhadawari", "benefit": "Enhances fat content further for ghee production"}
        ],
        "morphological_features": {
            "cranial_structure": "Broad flat forehead; massive head — primary buffalo identification signal",
            "horn_curvature": "Tightly coiled clockwise spiral — the most distinctive Murrah feature",
            "dewlap": "Absent (buffalo); thick neck",
            "ears": "Short, funnel-shaped, upright",
            "coat": "Jet black; sparse hair; thick skin",
            "body": "Heavy, compact; large, well-attached udder with prominent milk veins"
        },
        "explanation_sentence": "This is a Murrah buffalo — the AI's heatmap activates most strongly on the tightly coiled spiral horns and jet-black coat, which are the two most discriminating features separating Murrah from other buffalo breeds like Surti or Jaffarabadi.",
        "data_status": "curated"
    },
    "Kankrej": {
        "category": "Indigenous Dual-Purpose Cattle",
        "native_tract": "Rann of Kutch, Banaskantha, Mehsana — Gujarat/Rajasthan border",
        "native_states": ["Gujarat", "Rajasthan"],
        "avg_milk_yield": "1,400 – 2,200 kg / lactation",
        "speciality": "Dual-purpose (milk + draught); parent of American Brahman; extremely hardy in arid conditions.",
        "temperament": "Active, spirited — harder to manage than Gir/Sahiwal",
        "purpose": "Dual Purpose",
        "disease_resistance": "Outstanding drought and heat tolerance; good tick resistance",
        "optimal_crossbreeding": "Kankrej × Jersey for milk improvement while retaining draught capacity.",
        "crossbreeding_partners": [
            {"breed": "Jersey", "benefit": "Triples milk yield while retaining heat tolerance and draught ability"},
            {"breed": "Gir", "benefit": "Improves milk yield; well-adapted to same arid Gujarat zone"},
            {"breed": "Tharparkar", "benefit": "Reinforces drought tolerance; suited to desert border regions"}
        ],
        "morphological_features": {
            "cranial_structure": "Broad, slightly domed — shorter poll than Gir",
            "horn_curvature": "Lyre-shaped: rising outward then curving inward and up — highly distinctive",
            "dewlap": "Large; well-developed",
            "ears": "Long, narrow, horizontal",
            "coat": "Silver-grey to iron-grey; short, sleek",
            "body": "Large, powerful; massive hump; muscular quarters"
        },
        "explanation_sentence": "The AI identified Kankrej from the signature lyre-shaped horns and silver-grey coat — the attention heatmap shows strong focus on the horn bases and the withers hump, features that clearly separate Kankrej from the similarly-coloured Tharparkar.",
        "data_status": "curated"
    },
    "Khillari": {
        "category": "Indigenous Draught Cattle",
        "native_tract": "Sholapur, Satara, Sangli districts — Maharashtra/Karnataka border",
        "native_states": ["Maharashtra", "Karnataka"],
        "avg_milk_yield": "700 – 900 kg / lactation (draught breed)",
        "speciality": "One of India's finest draught breeds; renowned for speed and stamina on rocky Deccan terrain.",
        "temperament": "Energetic, alert — requires experienced handling",
        "purpose": "Draught",
        "disease_resistance": "Highly adapted to dry rocky terrain; good resistance to tick-borne diseases",
        "optimal_crossbreeding": "Limited crossbreeding recommended to preserve draught genetics.",
        "crossbreeding_partners": [
            {"breed": "Hariana", "benefit": "Introduces dairy capacity while retaining some draught utility"},
            {"breed": "Ongole", "benefit": "Increases body weight and pulling power for heavier agricultural loads"}
        ],
        "morphological_features": {
            "cranial_structure": "Long, narrow, lean head — alert expression",
            "horn_curvature": "Long, forward-pointing, tapering to a fine tip — sword-shaped",
            "dewlap": "Thin, small — minimal compared to milch breeds",
            "ears": "Small, horizontal, alert",
            "coat": "White to grey; tight, glossy",
            "body": "Compact, tight-skinned; well-developed hindquarters for speed"
        },
        "explanation_sentence": "Khillari was identified from the combination of its long sword-shaped forward-pointing horns, lean head, and compact grey body — the AI's heatmap shows focused activation on the horn profile and tight flanks, which differentiate it from the heavier Ongole draught breed.",
        "data_status": "curated"
    },
    "Hariana": {
        "category": "Indigenous Dual-Purpose Cattle",
        "native_tract": "Rohtak, Hisar, Gurgaon districts — Haryana",
        "native_states": ["Haryana", "Uttar Pradesh", "Delhi"],
        "avg_milk_yield": "1,200 – 1,800 kg / lactation",
        "speciality": "Versatile dual-purpose breed; widely used in government breeding programmes; strong draught animals.",
        "temperament": "Docile, easy to manage",
        "purpose": "Dual Purpose",
        "disease_resistance": "Moderate; well-adapted to sub-tropical plains climate",
        "optimal_crossbreeding": "HF × Hariana for improved dairy yield in Haryana government programmes.",
        "crossbreeding_partners": [
            {"breed": "Holstein Friesian", "benefit": "Government-recommended cross for UP/Haryana milk belts; 10–14 L/day"},
            {"breed": "Sahiwal", "benefit": "Improves tick resistance and milk fat for Punjab-belt dairy"},
            {"breed": "Jersey", "benefit": "Improves milk yield on smaller farms needing lower feed inputs"}
        ],
        "morphological_features": {
            "cranial_structure": "Long, narrow, slightly convex — less pronounced than Gir",
            "horn_curvature": "Short, outward and upward curve",
            "dewlap": "Moderate",
            "ears": "Medium; horizontal",
            "coat": "White to light grey; fine short hair",
            "body": "Tall, long; deep chest; moderate hump"
        },
        "explanation_sentence": "The AI identified Hariana from the tall, long-bodied white-grey silhouette and moderately convex narrow head — the heatmap shows activation on the topline and withers, confirming the body-proportion cues that separate Hariana from the more compact Sahiwal.",
        "data_status": "curated"
    },
    "Kangayam": {
        "category": "Indigenous Draught Cattle",
        "native_tract": "Erode and Tiruppur districts — Tamil Nadu",
        "native_states": ["Tamil Nadu"],
        "avg_milk_yield": "600 – 900 kg / lactation (draught breed)",
        "speciality": "Critically endangered South Indian draught breed; exceptional disease resistance; well-adapted to hot dry conditions.",
        "temperament": "Alert, active — hardy field worker",
        "purpose": "Draught",
        "disease_resistance": "Outstanding resistance to foot-and-mouth, HS, and tick-borne diseases in dry tropical climate",
        "optimal_crossbreeding": "Conservation priority — crossbreeding is discouraged to prevent genetic erosion.",
        "crossbreeding_partners": [
            {"breed": "Umblachery", "benefit": "Regional cross used in Tamil Nadu coastal areas; retains hardiness"}
        ],
        "morphological_features": {
            "cranial_structure": "Broad, flat forehead; short compact head",
            "horn_curvature": "Outward and upward — wide lyre shape",
            "dewlap": "Small to moderate",
            "ears": "Medium; slightly drooping",
            "coat": "Grey to dark grey; short dense hair",
            "body": "Compact, muscular; medium hump; deep chest"
        },
        "explanation_sentence": "Kangayam was identified from the wide lyre-shaped horns, compact grey body, and distinctive Tamil Nadu regional morphology — the AI's heatmap activates on the horn spread and compact withers, features that distinguish it from the similarly-grey Kankrej found in north-west India.",
        "data_status": "curated"
    },
    "Tharparkar": {
        "category": "Indigenous Dual-Purpose Cattle",
        "native_tract": "Thar Desert — Barmer, Jodhpur districts, Rajasthan",
        "native_states": ["Rajasthan"],
        "avg_milk_yield": "1,600 – 2,400 kg / lactation",
        "speciality": "Best milk yield among Indian desert breeds; unmatched drought and heat tolerance; significant A2 milk producer.",
        "temperament": "Docile",
        "purpose": "Dual Purpose",
        "disease_resistance": "Exceptional drought tolerance; good resistance to tick-borne diseases in arid zones",
        "optimal_crossbreeding": "Sahiwal × Tharparkar strengthens desert dairy milk production.",
        "crossbreeding_partners": [
            {"breed": "Sahiwal", "benefit": "Improves lactation yield while retaining drought adaptation"},
            {"breed": "Rathi", "benefit": "Enhances milk fat in Rajasthan dairy belt"},
            {"breed": "Jersey", "benefit": "Increases daily yield on peri-urban Rajasthan farms"}
        ],
        "morphological_features": {
            "cranial_structure": "Long, slightly convex forehead",
            "horn_curvature": "Short, outward curving; tips pointing up",
            "dewlap": "Moderate",
            "ears": "Long, drooping horizontally",
            "coat": "White to grey-white; can have dark grey patches on face",
            "body": "Medium-large; deep compact barrel"
        },
        "explanation_sentence": "Tharparkar was identified from the white-to-grey coat with characteristic dark face patches and compact barrel body typical of desert-adapted Indian cattle — the heatmap shows activation on the muzzle and face region where the pigmentation contrast is most distinctive.",
        "data_status": "curated"
    },
    "Rathi": {
        "category": "Indigenous Milch Cattle",
        "native_tract": "Bikaner, Ganganagar, Hanumangarh — Rajasthan",
        "native_states": ["Rajasthan"],
        "avg_milk_yield": "1,400 – 2,100 kg / lactation",
        "speciality": "Best milch breed of Rajasthan; tolerates high temperatures and scarce water; moderate A2 milk content.",
        "temperament": "Docile, calm",
        "purpose": "Milch",
        "disease_resistance": "Adapted to extreme desert heat and low water availability",
        "optimal_crossbreeding": "HF × Rathi for Rajasthan cooperative dairy improvement.",
        "crossbreeding_partners": [
            {"breed": "Holstein Friesian", "benefit": "Rajasthan cooperative dairy programme standard cross; 12–16 L/day"},
            {"breed": "Tharparkar", "benefit": "Reinforces desert adaptation and milk fat"}
        ],
        "morphological_features": {
            "cranial_structure": "Broad, rounded forehead",
            "horn_curvature": "Short, curving outward and upward",
            "dewlap": "Moderate to large",
            "ears": "Medium; drooping slightly",
            "coat": "Brown to dark brown with white patches — distinctive spotted pattern",
            "body": "Medium; well-built; moderate hump"
        },
        "explanation_sentence": "The AI identified Rathi from the distinctive brown coat with irregular white patches — a coat pattern unique among Indian desert breeds — with heatmap attention focused on the body coat pattern and broad forehead that differentiate it from the all-white Tharparkar.",
        "data_status": "curated"
    },
    "Red Sindhi": {
        "category": "Indigenous Milch Cattle",
        "native_tract": "Sindh (origin); now distributed across Kerala, Karnataka, Tamil Nadu",
        "native_states": ["Kerala", "Karnataka", "Tamil Nadu", "Andhra Pradesh"],
        "avg_milk_yield": "1,800 – 2,600 kg / lactation",
        "speciality": "High heat and tick tolerance; uniform deep-red coat; significant A2 milk production; exported to many tropical countries.",
        "temperament": "Docile, calm",
        "purpose": "Milch",
        "disease_resistance": "Outstanding tick resistance; excellent heat tolerance; moderate disease resistance in humid tropics",
        "optimal_crossbreeding": "HF × Red Sindhi is the recommended cross for Kerala cooperative dairy.",
        "crossbreeding_partners": [
            {"breed": "Holstein Friesian", "benefit": "Kerala cooperative standard; 15–18 L/day in humid tropical conditions"},
            {"breed": "Jersey", "benefit": "Improves fat content; well-suited to hill stations"},
            {"breed": "Sahiwal", "benefit": "Strengthens tick resistance and dairy vigour"}
        ],
        "morphological_features": {
            "cranial_structure": "Broad, slightly domed forehead",
            "horn_curvature": "Short, thick; curving outward and upward",
            "dewlap": "Large, pendulous",
            "ears": "Medium; drooping horizontally",
            "coat": "Deep uniform dark red — the most distinctive single-feature identifier",
            "body": "Medium; loose skin; moderate hump"
        },
        "explanation_sentence": "Red Sindhi was identified primarily from its uniform deep-red coat colour — the single most discriminating visual feature — with the AI's heatmap confirming attention concentrated on the coat across the barrel and shoulder, distinguishing it from the similar-sized but lighter Sahiwal.",
        "data_status": "curated"
    },
    "Ongole": {
        "category": "Indigenous Dual-Purpose Cattle",
        "native_tract": "Ongole, Guntur, Prakasam districts — Andhra Pradesh",
        "native_states": ["Andhra Pradesh", "Telangana"],
        "avg_milk_yield": "1,300 – 1,800 kg / lactation",
        "speciality": "Iconic draught breed of coastal Andhra; massive body; exported globally as Nellore cattle to Brazil and the USA.",
        "temperament": "Active, bold",
        "purpose": "Dual Purpose (draught-primary)",
        "disease_resistance": "Excellent tick and screwworm resistance; well-adapted to hot humid coastal climate",
        "optimal_crossbreeding": "Ongole × Sahiwal for improved dairy output while retaining tropical draught capacity.",
        "crossbreeding_partners": [
            {"breed": "Sahiwal", "benefit": "Improves dairy output in Andhra coastal dairy belt"},
            {"breed": "Gir", "benefit": "Enhances milk yield while retaining heat-tolerant draught genetics"}
        ],
        "morphological_features": {
            "cranial_structure": "Long, broad, massive head; prominent poll",
            "horn_curvature": "Thick at base; spreading outward then curving inward",
            "dewlap": "Very large, heavily folded — distinctive Ongole signature",
            "ears": "Large, horizontal, pendulous",
            "coat": "White to grey; short, glossy",
            "body": "Very large, heavy; massive cervico-thoracic hump; powerful quarters"
        },
        "explanation_sentence": "The AI identified this as an Ongole from the combination of massive body size, very large heavily-folded dewlap, and prominent poll — the heatmap shows the strongest activation on the dewlap and shoulder hump region, which together form the most distinctive visual signature of this coastal Andhra breed.",
        "data_status": "curated"
    },
    "Vechur": {
        "category": "Indigenous Milch Cattle (Endangered)",
        "native_tract": "Kottayam, Ernakulam districts — Kerala",
        "native_states": ["Kerala"],
        "avg_milk_yield": "500 – 900 kg / lactation (world's smallest breed)",
        "speciality": "World's smallest cattle breed; high A2 milk fat (4.5%+); under active conservation by Kerala Veterinary & Animal Sciences University.",
        "temperament": "Extremely docile and easy to manage",
        "purpose": "Milch (low-input smallholder farming)",
        "disease_resistance": "High resistance to common cattle diseases in humid Kerala climate; tick-tolerant",
        "optimal_crossbreeding": "Conservation priority — crossbreeding is actively discouraged to prevent extinction.",
        "crossbreeding_partners": [
            {"breed": "None recommended", "benefit": "Breed is critically endangered; pure breeding is the priority under KVASU conservation programme"}
        ],
        "morphological_features": {
            "cranial_structure": "Very small head; slightly dished profile",
            "horn_curvature": "Very short; slightly curved outward",
            "dewlap": "Minimal",
            "ears": "Small, upright",
            "coat": "Red-brown to fawn; short, glossy",
            "body": "Extremely small (smallest cattle breed in the world); compact; light-boned"
        },
        "explanation_sentence": "Vechur was identified from its uniquely miniature body size and proportionally small head — the AI's heatmap activates strongly on the overall body silhouette and the exceptionally small horn size, which are the primary classification signals separating it from all other Indian dairy breeds.",
        "data_status": "curated"
    },
    "Holstein Friesian": {
        "category": "Exotic Dairy Cattle",
        "native_tract": "Netherlands / Northern Germany; distributed globally including India",
        "native_states": ["Punjab", "Haryana", "Maharashtra", "Karnataka"],
        "avg_milk_yield": "6,000 – 9,000 kg / lactation",
        "speciality": "World's highest-yielding dairy cattle; used in crossbreeding programmes across India for milk yield improvement.",
        "temperament": "Calm but requires good nutrition and management",
        "purpose": "High-input Milch",
        "disease_resistance": "Low tick resistance; heat-sensitive; requires temperate or controlled environments",
        "optimal_crossbreeding": "HF × Sahiwal, HF × Rathi, HF × Hariana — standard government crossbreeding programmes.",
        "crossbreeding_partners": [
            {"breed": "Sahiwal", "benefit": "National recommended cross; 15–18 L/day with tropical adaptation"},
            {"breed": "Rathi", "benefit": "Rajasthan cooperative cross; adapts HF genetics to desert climate"},
            {"breed": "Red Sindhi", "benefit": "Kerala cooperative cross; retains humid-climate tolerance"}
        ],
        "morphological_features": {
            "cranial_structure": "Broad, flat forehead; angular face — typical dairy wedge shape",
            "horn_curvature": "Short, fine; slightly outward",
            "dewlap": "Small and tight",
            "ears": "Medium; horizontal",
            "coat": "Black-and-white patches — instantly recognisable pattern",
            "body": "Large, angular; prominent ribs visible; very large udder"
        },
        "explanation_sentence": "Holstein Friesian was identified from its distinctive high-contrast black-and-white patched coat — the most recognisable coat pattern in dairy cattle globally — with the AI's heatmap showing strong activation across the body coat and the prominent dairy-wedge body shape.",
        "data_status": "curated"
    },
    "Jersey": {
        "category": "Exotic Dairy Cattle",
        "native_tract": "Jersey Island, Channel Islands; widespread in India",
        "native_states": ["Kerala", "Karnataka", "Tamil Nadu", "Himachal Pradesh"],
        "avg_milk_yield": "4,000 – 6,000 kg / lactation (high butterfat 5–6%)",
        "speciality": "Highest butterfat percentage of any major dairy breed; performs well in hill stations; better heat tolerance than HF among exotics.",
        "temperament": "Docile but can be timid",
        "purpose": "Milch (butterfat focus)",
        "disease_resistance": "Better heat tolerance than Holstein Friesian; moderate tick susceptibility",
        "optimal_crossbreeding": "Jersey × Gir for A2-rich high-fat milk on Indian mixed farms.",
        "crossbreeding_partners": [
            {"breed": "Gir", "benefit": "High-fat A2 milk with good heat tolerance for Gujarat/Maharashtra"},
            {"breed": "Sahiwal", "benefit": "Improved heat and tick tolerance for Punjab-belt dairy"},
            {"breed": "Red Sindhi", "benefit": "Kerala cooperative cross for high-fat milk in humid climate"}
        ],
        "morphological_features": {
            "cranial_structure": "Refined, deer-like small head; large bright eyes; dished profile",
            "horn_curvature": "Small, fine, crescent-shaped",
            "dewlap": "Very small",
            "ears": "Medium; upright-to-slightly-drooping",
            "coat": "Fawn to dark brown; can have black muzzle; uniform colour",
            "body": "Small to medium; fine-boned; very angular dairy wedge; large udder relative to body"
        },
        "explanation_sentence": "Jersey was identified from its refined deer-like small head with a characteristic dished profile, large expressive eyes, and uniform fawn-to-brown coat — the AI's heatmap shows focused attention on the facial structure and fine bone, features that immediately distinguish Jersey from similarly-coloured indigenous breeds like Sahiwal.",
        "data_status": "curated"
    },
    "Surti": {
        "category": "Indigenous Buffalo",
        "native_tract": "Kaira and Baroda districts — Gujarat",
        "native_states": ["Gujarat"],
        "avg_milk_yield": "1,700 – 2,500 kg / lactation",
        "speciality": "Best milk-fat buffalo breed of Gujarat (8.5–9% fat); suited to coastal and riparian environments.",
        "temperament": "Docile, manageable",
        "purpose": "Milch Buffalo",
        "disease_resistance": "Good adaptation to humid coastal Gujarat; moderate tick resistance",
        "optimal_crossbreeding": "Surti × Murrah is recommended to introduce high-yield Murrah genetics into Gujarat herds.",
        "crossbreeding_partners": [
            {"breed": "Murrah", "benefit": "Increases lactation yield significantly while retaining coastal adaptability"},
            {"breed": "Mehsana", "benefit": "Improves yield in northern Gujarat dairy cooperatives"}
        ],
        "morphological_features": {
            "cranial_structure": "Flat, broad forehead — typical buffalo",
            "horn_curvature": "Sickle-shaped: rising and curving backward then inward — distinct from Murrah's spiral",
            "dewlap": "Absent (buffalo); thick neck",
            "ears": "Short, funnel-shaped",
            "coat": "Black or rusty brown; sparse hair",
            "body": "Medium-large; wedge-shaped; well-attached udder"
        },
        "explanation_sentence": "Surti buffalo was identified from its sickle-shaped horns — curving backward and inward rather than spiralling — which is the primary visual feature separating Surti from Murrah; the AI's heatmap shows peak activation on the horn curvature and the lighter rusty-brown coat variation.",
        "data_status": "curated"
    }
}

def get_breed_profile(breed_name: str) -> dict:
    """Return full breed profile, falling back gracefully for unlisted breeds."""
    # Try exact match first
    if breed_name in BREED_PROFILES:
        return BREED_PROFILES[breed_name]
    # Try case-insensitive partial match
    bl = breed_name.lower()
    for key, val in BREED_PROFILES.items():
        if key.lower() in bl or bl in key.lower():
            return val
    # Default fallback
    return {
        "category": "Livestock",
        "native_tract": "Data pending",
        "native_states": [],
        "avg_milk_yield": "Data pending",
        "speciality": "Full profile pending — breed data will be added in the next model update.",
        "temperament": "Unknown",
        "purpose": "Unknown",
        "disease_resistance": "Unknown",
        "optimal_crossbreeding": "Profile pending.",
        "crossbreeding_partners": [],
        "morphological_features": {
            "cranial_structure": "Not yet characterised",
            "horn_curvature": "Not yet characterised",
            "dewlap": "Not yet characterised",
            "ears": "Not yet characterised",
            "coat": "Not yet characterised",
            "body": "Not yet characterised"
        },
        "explanation_sentence": "Breed profile is pending. The AI identified this animal based on overall morphological similarity — please refer to the Grad-CAM heatmap for the specific regions that drove the classification.",
        "data_status": "pending"
    }


@app.route("/")
@app.route("/api/index.py")
def index():
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        return render_template_string(
            content,
            engine=MockEngine(),
            total_breeds=60,
            active_learning_count=3,
            verified_count=142,
            threshold=0.70
        )
    return "<h3>Error: index.html not found.</h3>", 404


@app.route("/static/<path:filename>")
def serve_static(filename):
    path = os.path.join(DASHBOARD_DIR, "static", filename)
    if os.path.exists(path):
        return send_file(path)
    return f"Asset {filename} not found", 404


# ── 1. Prediction / Scan Route ────────────────────────────────────────────────
@app.route("/predict", methods=["GET", "POST"])
@app.route("/api/predict", methods=["GET", "POST"])
@app.route("/api/scan", methods=["GET", "POST"])
@app.route("/scan", methods=["GET", "POST"])
def predict():
    region = request.form.get("region", "Gujarat")
    color  = request.form.get("color", "Reddish Brown")
    lat_raw = request.form.get("latitude", "").strip()
    lon_raw = request.form.get("longitude", "").strip()
    try:
        latitude = float(lat_raw) if lat_raw else None
    except ValueError:
        latitude = None
    try:
        longitude = float(lon_raw) if lon_raw else None
    except ValueError:
        longitude = None

    # Simple demo logic — in production this comes from the inference engine
    if "Gujarat" in region or "Red" in color:
        breed_name = "Gir Cattle"
    elif "Punjab" in region or "Haryana" in region:
        breed_name = "Sahiwal"
    elif "buffalo" in color.lower():
        breed_name = "Murrah"
    else:
        breed_name = "Holstein Friesian"

    profile = get_breed_profile(breed_name)
    timestamp   = time.strftime("%Y-%m-%d %H:%M:%S")
    record_hash = hashlib.sha256(f"{breed_name}{timestamp}".encode()).hexdigest()

    geo_tag = f"{latitude:.4f}°, {longitude:.4f}°" if (latitude is not None and longitude is not None) else None

    response_payload = {
        "success": True,
        "breed": breed_name,
        # ── keys expected by populateResults() ──
        "top1_breed": breed_name,
        "category": profile["category"],
        "confidence": 0.948,
        "top_prediction": breed_name,
        "top3": [
            {"breed": breed_name,   "confidence": 0.948},
            {"breed": "Red Sindhi", "confidence": 0.034},
            {"breed": "Kankrej",    "confidence": 0.018}
        ],
        # Full enriched breed details block
        "breed_details": {
            "category":             profile["category"],
            "native_tract":         profile["native_tract"],
            "native_states":        profile["native_states"],
            "avg_milk_yield":       profile["avg_milk_yield"],
            "speciality":           profile["speciality"],
            "temperament":          profile["temperament"],
            "purpose":              profile["purpose"],
            "disease_resistance":   profile["disease_resistance"],
            "optimal_crossbreeding":profile["optimal_crossbreeding"],
            "crossbreeding_partners":profile["crossbreeding_partners"],
            "data_status":          profile["data_status"]
        },
        # Morphological features for XAI card
        "morphological_features": profile["morphological_features"],
        # Plain-language explanation for XAI card
        "explanation_sentence": profile["explanation_sentence"],
        # GradCAM images
        "gradcam": {
            "original": GRAD_CAM_ORIGINAL,
            "heatmap":  GRAD_CAM_HEATMAP
        },
        "image_url":     GRAD_CAM_ORIGINAL,
        "xai_image_url": GRAD_CAM_HEATMAP,
        # Location
        "latitude":          latitude,
        "longitude":         longitude,
        "geo_tag":           geo_tag,
        # Audit
        "region_boosted":    "Gujarat" in region or "Punjab" in region,
        "status":            "AUTO_VERIFIED",
        "blockchain_hash":   record_hash,
        "sha256_hash":       record_hash,
        "hash":              record_hash,
        "pashu_aadhaar":     f"PA-{record_hash[:8].upper()}",
        "qr_code_url":       GRAD_CAM_ORIGINAL,
        "timestamp":         timestamp
    }

    return jsonify({
        **response_payload,
        "prediction": response_payload,
        "data":       response_payload,
        "result":     response_payload
    })


# ── 2. Encyclopedia / Breed Info Route ────────────────────────────────────────
@app.route("/api/breeds",       methods=["GET"])
@app.route("/api/catalog",      methods=["GET"])
@app.route("/breeds",           methods=["GET"])
@app.route("/catalog",          methods=["GET"])
@app.route("/encyclopedia",     methods=["GET"])
@app.route("/api/encyclopedia", methods=["GET"])
def catalog():
    breeds_data = []
    for name, p in BREED_PROFILES.items():
        breeds_data.append({
            "id":                     str(len(breeds_data) + 1),
            "breed_name":             name,
            "name":                   name,
            "breed":                  name,
            "category":               p["category"],
            "origin":                 p["native_states"][0] if p["native_states"] else "India",
            "native_tract":           p["native_tract"],
            "native_states":          p["native_states"],
            "avg_milk_yield":         p["avg_milk_yield"],
            "milk_yield":             p["avg_milk_yield"],
            "production_yield":       p["avg_milk_yield"],
            "speciality":             p["speciality"],
            "traits":                 p["speciality"],
            "purpose":                p["purpose"],
            "temperament":            p["temperament"],
            "disease_resistance":     p["disease_resistance"],
            "optimal_crossbreeding":  p["optimal_crossbreeding"],
            "crossbreeding_partners": p["crossbreeding_partners"],
            "morphological_features": p["morphological_features"],
            "explanation_sentence":   p["explanation_sentence"],
            "image_url":              f"/static/images/{name.lower().replace(' ','_')}.jpg"
        })
    return jsonify({
        "success": True,
        "breeds":  breeds_data,
        "data":    breeds_data,
        "catalog": breeds_data,
        "items":   breeds_data,
        "records": breeds_data
    })


# ── 3. Expert Verification Queue Route ────────────────────────────────────────
@app.route("/api/queue",        methods=["GET"])
@app.route("/api/expert-queue", methods=["GET"])
@app.route("/queue",            methods=["GET"])
@app.route("/expert-queue",     methods=["GET"])
@app.route("/api/review",       methods=["GET"])
def queue():
    queue_items = [
        {
            "id":             "SCN-9042",
            "scan_id":        "SCN-9042",
            "image":          "/static/images/sample1.jpg",
            "image_url":      "/static/images/sample1.jpg",
            "image_path":     "/static/images/sample1.jpg",
            "top_prediction": "Kankrej (64.2%)",
            "prediction":     "Kankrej",
            "breed":          "Kankrej",
            "predicted_breed":"Kankrej",
            "confidence":     0.642,
            "confidence_score": 0.642,
            "region_input":   "Rajasthan",
            "color_input":    "Silver Grey",
            "metadata":       "Rajasthan • Silver Grey Coat • Age: 4y",
            "status":         "flagged_for_expert",
            "actions":        ["Approve", "Reclassify"]
        },
        {
            "id":             "SCN-9043",
            "scan_id":        "SCN-9043",
            "image":          "/static/images/sample2.jpg",
            "image_url":      "/static/images/sample2.jpg",
            "image_path":     "/static/images/sample2.jpg",
            "top_prediction": "Red Sindhi (61.8%)",
            "prediction":     "Red Sindhi",
            "breed":          "Red Sindhi",
            "predicted_breed":"Red Sindhi",
            "confidence":     0.618,
            "confidence_score": 0.618,
            "region_input":   "Gujarat",
            "color_input":    "Dark Red",
            "metadata":       "Gujarat • Dark Red Coat • Age: 2y",
            "status":         "flagged_for_expert",
            "actions":        ["Approve", "Reclassify"]
        }
    ]
    return jsonify({
        "success": True,
        "queue":   queue_items,
        "data":    queue_items,
        "items":   queue_items,
        "scans":   queue_items,
        "records": queue_items
    })


# ── 4. Audit Trail Route ───────────────────────────────────────────────────────
@app.route("/api/audit",       methods=["GET"])
@app.route("/api/audit-trail", methods=["GET"])
@app.route("/api/history",     methods=["GET"])
@app.route("/audit",           methods=["GET"])
@app.route("/audit-trail",     methods=["GET"])
@app.route("/history",         methods=["GET"])
def audit():
    audit_data = [
        {
            "id":              "SCN-842",
            "timestamp":       "2026-08-24 22:15:10",
            "image":           "scan_842.jpg",
            "image_url":       "/static/images/gir.jpg",
            "image_path":      "/static/images/gir.jpg",
            "breed":           "Gir Cattle",
            "predicted_breed": "Gir Cattle",
            "confidence":      0.948,
            "confidence_score":0.948,
            "status":          "verified",
            "blockchain_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "record_hash":     "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "hash":            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        },
        {
            "id":              "SCN-841",
            "timestamp":       "2026-08-24 21:40:02",
            "image":           "scan_841.jpg",
            "image_url":       "/static/images/murrah.jpg",
            "image_path":      "/static/images/murrah.jpg",
            "breed":           "Murrah Buffalo",
            "predicted_breed": "Murrah",
            "confidence":      0.961,
            "confidence_score":0.961,
            "status":          "verified",
            "blockchain_hash": "8f4e2c91b1a7d3e6f0b8c4d2e1a9f3b5c7e8d2a1b4c6e9f0a2d3b5c7e8f1a2b3",
            "record_hash":     "8f4e2c91b1a7d3e6f0b8c4d2e1a9f3b5c7e8d2a1b4c6e9f0a2d3b5c7e8f1a2b3",
            "hash":            "8f4e2c91b1a7d3e6f0b8c4d2e1a9f3b5c7e8d2a1b4c6e9f0a2d3b5c7e8f1a2b3"
        },
        {
            "id":              "SCN-840",
            "timestamp":       "2026-08-24 20:12:44",
            "image":           "scan_840.jpg",
            "image_url":       "/static/images/sahiwal.jpg",
            "image_path":      "/static/images/sahiwal.jpg",
            "breed":           "Sahiwal Cattle",
            "predicted_breed": "Sahiwal",
            "confidence":      0.913,
            "confidence_score":0.913,
            "status":          "verified",
            "blockchain_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef01",
            "record_hash":     "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef01",
            "hash":            "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef01"
        }
    ]
    return jsonify({
        "success": True,
        "audit":   audit_data,
        "logs":    audit_data,
        "data":    audit_data,
        "items":   audit_data,
        "scans":   audit_data,
        "records": audit_data
    })


# ── 5. Verification & Sync Action Routes ──────────────────────────────────────
@app.route("/api/verify",  methods=["POST", "GET"])
@app.route("/verify",      methods=["POST", "GET"])
@app.route("/api/sync",    methods=["POST", "GET"])
@app.route("/sync",        methods=["POST", "GET"])
@app.route("/api/retrain", methods=["POST", "GET"])
@app.route("/retrain",     methods=["POST", "GET"])
def verify():
    return jsonify({"success": True, "message": "Record confirmed and synced to BPA registry."})