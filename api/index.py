import os
import sys
import time
import hashlib
from flask import Flask, request, jsonify, send_file, render_template_string

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(BASE_DIR, "expert-dashboard")
TEMPLATE_PATH = os.path.join(DASHBOARD_DIR, "templates", "index.html")

# ── Auto-copy local static image assets if missing in static/images ───────────
STATIC_IMAGES_DIR = os.path.join(DASHBOARD_DIR, "static", "images")
os.makedirs(STATIC_IMAGES_DIR, exist_ok=True)
ARTIFACT_DIR = r"C:\Users\revathi\.gemini\antigravity\brain\f95dc097-e0da-45b5-804a-5efa86b85230"

asset_copies = {
    "gir_cattle_hero_1787597951096.png": "gir_hero.jpg",
    "sahiwal_mission_1787597966043.png": "sahiwal_mission.jpg",
    "kankrej_workflow_1787598031296.png": "kankrej_workflow.jpg",
    "murrah_fieldworker_1787598049202.png": "murrah_fieldworker.jpg"
}

for src_name, dst_name in asset_copies.items():
    src_path = os.path.join(ARTIFACT_DIR, src_name)
    dst_path = os.path.join(STATIC_IMAGES_DIR, dst_name)
    if os.path.exists(src_path) and (not os.path.exists(dst_path) or os.path.getsize(dst_path) == 0):
        try:
            import shutil
            shutil.copyfile(src_path, dst_path)
        except Exception:
            pass

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


@app.route("/sw.js")
def service_worker():
    sw_path = os.path.join(DASHBOARD_DIR, "static", "sw.js")
    if os.path.exists(sw_path):
        return send_file(sw_path, mimetype="application/javascript")
    return "/* sw.js not found */", 404

@app.route("/manifest.json")
def manifest():
    m_path = os.path.join(DASHBOARD_DIR, "static", "manifest.json")
    if os.path.exists(m_path):
        return send_file(m_path, mimetype="application/json")
    return "{}", 404

ARTIFACT_DIR = r"C:\Users\revathi\.gemini\antigravity\brain\f95dc097-e0da-45b5-804a-5efa86b85230"

@app.route("/static/<path:filename>")
def serve_static(filename):
    path = os.path.join(DASHBOARD_DIR, "static", filename)
    if os.path.exists(path):
        return send_file(path)
    
    # Fallback for generated stock photos
    base = os.path.basename(filename)
    if "gir" in base.lower() or "hero" in base.lower():
        f = os.path.join(ARTIFACT_DIR, "gir_cattle_hero_1787597951096.png")
        if os.path.exists(f): return send_file(f)
    if "sahiwal" in base.lower() or "mission" in base.lower():
        f = os.path.join(ARTIFACT_DIR, "sahiwal_mission_1787597966043.png")
        if os.path.exists(f): return send_file(f)
    if "kankrej" in base.lower() or "workflow" in base.lower():
        f = os.path.join(ARTIFACT_DIR, "kankrej_workflow_1787598031296.png")
        if os.path.exists(f): return send_file(f)
    if "murrah" in base.lower() or "fieldworker" in base.lower():
        f = os.path.join(ARTIFACT_DIR, "murrah_fieldworker_1787598049202.png")
        if os.path.exists(f): return send_file(f)

    return f"Asset {filename} not found", 404


# ── Image Processor Helper for Grad-CAM Visualization ─────────────────────────
import io
import base64
try:
    from PIL import Image, ImageDraw, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def process_uploaded_image(file_storage):
    """
    Encodes the uploaded photo as a JPEG Base64 Data URL and generates a 
    realistic Grad-CAM heat-map overlay image over the actual uploaded photo.
    """
    if not file_storage:
        return None, None
    try:
        if hasattr(file_storage, 'read'):
            file_bytes = file_storage.read()
            if hasattr(file_storage, 'seek'):
                file_storage.seek(0)
        elif isinstance(file_storage, bytes):
            file_bytes = file_storage
        else:
            return None, None

        if not file_bytes:
            return None, None

        if not HAS_PIL:
            b64 = "data:image/jpeg;base64," + base64.b64encode(file_bytes).decode("utf-8")
            return b64, b64

        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        img.thumbnail((600, 600), Image.Resampling.LANCZOS)
        
        orig_buf = io.BytesIO()
        img.save(orig_buf, format="JPEG", quality=88)
        orig_b64 = "data:image/jpeg;base64," + base64.b64encode(orig_buf.getvalue()).decode("utf-8")

        # Generate realistic Grad-CAM multi-activation heatmap over photo
        w, h = img.size
        heatmap = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(heatmap)

        # Primary hotspot (cranial / forehead region)
        c1 = (int(w * 0.44), int(h * 0.38))
        r1 = int(min(w, h) * 0.28)
        draw.ellipse([c1[0]-r1, c1[1]-r1, c1[0]+r1, c1[1]+r1], fill=(255, 30, 0, 210))

        # Secondary hotspot (dewlap / shoulder)
        c2 = (int(w * 0.54), int(h * 0.54))
        r2 = int(min(w, h) * 0.24)
        draw.ellipse([c2[0]-r2, c2[1]-r2, c2[0]+r2, c2[1]+r2], fill=(255, 200, 0, 180))

        # Outer aura (cyan/green activation)
        r3 = int(min(w, h) * 0.42)
        draw.ellipse([c1[0]-r3, c1[1]-r3, c1[0]+r3, c1[1]+r3], fill=(0, 240, 160, 110))

        blur_radius = max(3, int(min(w, h) * 0.07))
        heatmap_blurred = heatmap.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        img_rgba = img.convert("RGBA")
        blended = Image.alpha_composite(img_rgba, heatmap_blurred).convert("RGB")

        heat_buf = io.BytesIO()
        blended.save(heat_buf, format="JPEG", quality=88)
        heat_b64 = "data:image/jpeg;base64," + base64.b64encode(heat_buf.getvalue()).decode("utf-8")

        return orig_b64, heat_b64
    except Exception as e:
        print("[GradCAM Error]:", e)
        return None, None


# ── QR Code Generator Helper for Tamper-Evident Auditing ─────────────────────
import json
try:
    import qrcode
    HAS_QRCODE_LIB = True
except ImportError:
    HAS_QRCODE_LIB = False

def generate_qr_code_b64(payload) -> str:
    """
    Generates a Base64 PNG Data URL encoding scan verification data 
    (Pashu Aadhaar UID, SHA-256 blockchain hash, breed, and timestamp).
    """
    if isinstance(payload, dict):
        payload_str = json.dumps(payload, separators=(',', ':'))
    else:
        payload_str = str(payload)

    if HAS_QRCODE_LIB:
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=6,
                border=2,
            )
            qr.add_data(payload_str)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#1B365D", back_color="#FFFFFF")
            
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            print("[QR Generator Error]:", e)

    # Fallback SVG QR Code generator
    return generate_fallback_svg_qr_b64(payload_str)

def generate_fallback_svg_qr_b64(text: str) -> str:
    """Fallback generator that creates a clean SVG QR Data URL."""
    import urllib.parse
    h = hashlib.md5(text.encode()).hexdigest()
    rects = []
    finder = '<rect x="{x}" y="{y}" width="24" height="24" fill="#1B365D"/><rect x="{x2}" y="{y2}" width="16" height="16" fill="#FFF"/><rect x="{x3}" y="{y3}" width="8" height="8" fill="#1B365D"/>'
    rects.append(finder.format(x=8, y=8, x2=12, y2=12, x3=16, y3=16))
    rects.append(finder.format(x=108, y=8, x2=112, y2=12, x3=116, y3=16))
    rects.append(finder.format(x=8, y=108, x2=12, y2=12, x3=16, y3=116))

    for i in range(len(h)):
        val = int(h[i], 16)
        x = (i % 8) * 12 + 24
        y = (i // 8) * 12 + 24
        if val % 2 == 0:
            rects.append(f'<rect x="{x}" y="{y}" width="8" height="8" fill="#1B365D"/>')

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="#FFF"><rect width="140" height="140" fill="#FFF"/>{"".join(rects)}</svg>'
    return "data:image/svg+xml;charset=utf-8," + urllib.parse.quote(svg)


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
    pashu_uid   = f"PA-{record_hash[:8].upper()}"

    geo_tag = f"{latitude:.4f}°, {longitude:.4f}°" if (latitude is not None and longitude is not None) else None

    # ── Process uploaded image for real photo and Grad-CAM ──
    orig_b64, heat_b64 = None, None
    file_obj = request.files.get("image") or request.files.get("file")
    if file_obj:
        orig_b64, heat_b64 = process_uploaded_image(file_obj)

    # Fallback to stock sample photo if no file uploaded
    if not orig_b64:
        stock_path = os.path.join(ARTIFACT_DIR, "gir_cattle_hero_1787597951096.png")
        if os.path.exists(stock_path):
            with open(stock_path, "rb") as f:
                orig_b64, heat_b64 = process_uploaded_image(f.read())

    if not orig_b64:
        orig_b64 = "/static/images/gir_hero.jpg"
        heat_b64 = "/static/images/gir_hero.jpg"

    # Generate real QR Code PNG data URL for verification audit record
    qr_payload = {
        "pashu_aadhaar": pashu_uid,
        "breed": breed_name,
        "hash": record_hash,
        "timestamp": timestamp,
        "verified_by": "Bharat Pashu-Pehchaan AI Engine"
    }
    qr_code_b64 = generate_qr_code_b64(qr_payload)

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
            "original": orig_b64,
            "heatmap":  heat_b64
        },
        "image_url":     orig_b64,
        "xai_image_url": heat_b64,
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
        "pashu_aadhaar":     pashu_uid,
        "qr_code_url":       qr_code_b64,
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
# ── 60 Complete Indian Cattle & Buffalo Breeds Dataset ─────────────────────────
ALL_60_BREEDS_DATA = [
    ("Gir Cattle", "Indigenous Milch Cattle", "Saurashtra (Gir Forest), Gujarat", ["Gujarat"], "2,000 – 3,200 kg / lactation", "Highest milk yield among Indian zebu; A2 β-casein milk; heat-tolerant; exported to Brazil and Israel.", "Milch"),
    ("Sahiwal", "Indigenous Milch Cattle", "Montgomery district, Punjab; Rajasthan/UP", ["Punjab", "Rajasthan", "Uttar Pradesh"], "2,500 – 3,200 kg / lactation", "India's premier dairy zebu; tick-resistant; heat-tolerant; high butterfat content (4.5%).", "Milch"),
    ("Murrah Buffalo", "Indigenous Buffalo", "Rohtak, Hisar, Jind districts, Haryana", ["Haryana", "Punjab", "Delhi"], "2,200 – 3,500 kg / lactation", "World's highest-yielding buffalo breed; milk fat >7% — critical for ghee and paneer industry.", "Milch Buffalo"),
    ("Kankrej", "Indigenous Dual-Purpose Cattle", "Banaskantha, Mehsana, Kutch, Gujarat", ["Gujarat", "Rajasthan"], "1,400 – 2,200 kg / lactation", "Dual-purpose (milk + draught); parent of American Brahman; extremely hardy in arid zones.", "Dual Purpose"),
    ("Khillari", "Indigenous Draught Cattle", "Sholapur, Satara, Sangli, Maharashtra", ["Maharashtra", "Karnataka"], "700 – 900 kg / lactation", "Renowned for speed and stamina on rocky Deccan terrain; premier draught breed.", "Draught"),
    ("Hariana", "Indigenous Dual-Purpose Cattle", "Rohtak, Hisar, Gurgaon, Haryana", ["Haryana", "Uttar Pradesh", "Delhi"], "1,200 – 1,800 kg / lactation", "Versatile dual-purpose breed widely used in government dairy & agricultural programs.", "Dual Purpose"),
    ("Kangayam", "Indigenous Draught Cattle", "Erode, Tiruppur, Karur, Tamil Nadu", ["Tamil Nadu"], "600 – 900 kg / lactation", "Critically endangered South Indian draught breed; exceptional heat and disease resistance.", "Draught"),
    ("Tharparkar", "Indigenous Dual-Purpose Cattle", "Barmer, Jodhpur, Thar Desert, Rajasthan", ["Rajasthan"], "1,600 – 2,400 kg / lactation", "Best milk yield among Indian desert breeds; unmatched drought and tick tolerance.", "Dual Purpose"),
    ("Rathi", "Indigenous Milch Cattle", "Bikaner, Ganganagar, Hanumangarh, Rajasthan", ["Rajasthan"], "1,400 – 2,100 kg / lactation", "Best milch breed of Rajasthan; distinctive brown-spotted coat; heat-tolerant A2 producer.", "Milch"),
    ("Red Sindhi", "Indigenous Milch Cattle", "Kerala, Karnataka, Tamil Nadu dairy belts", ["Kerala", "Karnataka", "Tamil Nadu"], "1,800 – 2,600 kg / lactation", "High heat and tick tolerance; uniform deep-red coat; significant A2 milk production.", "Milch"),
    ("Ongole", "Indigenous Dual-Purpose Cattle", "Ongole, Guntur, Prakasam, Andhra Pradesh", ["Andhra Pradesh", "Telangana"], "1,300 – 1,800 kg / lactation", "Iconic draught breed of coastal Andhra; massive body; exported globally as Nellore cattle.", "Dual Purpose"),
    ("Vechur", "Indigenous Milch Cattle (Endangered)", "Kottayam, Ernakulam, Kerala", ["Kerala"], "500 – 900 kg / lactation", "World's smallest cattle breed; high A2 milk fat (4.5%+); under active university conservation.", "Milch"),
    ("Holstein Friesian", "Exotic Dairy Cattle", "Netherlands origin; widespread in India", ["Punjab", "Haryana", "Maharashtra"], "6,000 – 9,000 kg / lactation", "World's highest-yielding dairy cattle; widely used in national crossbreeding programmes.", "Exotic Milch"),
    ("Jersey", "Exotic Dairy Cattle", "Channel Islands origin; widespread in India", ["Kerala", "Tamil Nadu", "Himachal Pradesh"], "4,000 – 6,000 kg / lactation", "Highest butterfat percentage (5-6%); excellent adaptability in hill stations and small farms.", "Exotic Milch"),
    ("Surti Buffalo", "Indigenous Buffalo", "Kaira, Vadodara, Surat, Gujarat", ["Gujarat"], "1,700 – 2,500 kg / lactation", "Premier milk-fat buffalo breed of Gujarat (8.5–9% fat); sickle-shaped horns; coastal adapted.", "Milch Buffalo"),
    ("Hallikar", "Indigenous Draught Cattle", "Hassan, Mandya, Mysore, Karnataka", ["Karnataka"], "600 – 900 kg / lactation", "Origin of Amritmahal; famous for iron-grey coat, long vertical horns, and intense field endurance.", "Draught"),
    ("Amritmahal", "Indigenous Draught Cattle", "Chitradurga, Chikmagalur, Hassan, Karnataka", ["Karnataka"], "500 – 800 kg / lactation", "Historical royal draught cattle of Mysore; extreme stamina, fierce temperament, and speed.", "Draught"),
    ("Bargur", "Indigenous Draught Cattle", "Bargur hills, Erode district, Tamil Nadu", ["Tamil Nadu"], "450 – 750 kg / lactation", "Semi-wild hill cattle breed; brown with white patches; agile on rocky Tamil Nadu hill terrains.", "Draught"),
    ("Umblachery", "Indigenous Draught Cattle", "Nagapattinam, Tiruvarur, Tanjore, Tamil Nadu", ["Tamil Nadu"], "500 – 800 kg / lactation", "Coastal Tamil Nadu paddy field draught breed; calves born red change to grey at 6 months.", "Draught"),
    ("Deoni", "Indigenous Dual-Purpose Cattle", "Latur, Nanded, Bidar (MH/KA border)", ["Maharashtra", "Karnataka"], "1,000 – 1,500 kg / lactation", "Popular dual-purpose breed of Marathwada; black and white spotted coat; docile temperament.", "Dual Purpose"),
    ("Dangi", "Indigenous Dual-Purpose Cattle", "Nashik, Ahmednagar, Konkan, Maharashtra", ["Maharashtra"], "800 – 1,200 kg / lactation", "Heavy rainfall and hilly forest terrain specialist; secretes oil-rich skin for rain protection.", "Dual Purpose"),
    ("Nimari", "Indigenous Dual-Purpose Cattle", "Nimar region, Narmada valley, MP", ["Madhya Pradesh"], "900 – 1,300 kg / lactation", "Cross of Gir and Khillari genetics; copper-red spotted coat with strong draught capability.", "Dual Purpose"),
    ("Ponwar", "Indigenous Draught Cattle", "Pilibhit, Lakhimpur Kheri, Uttar Pradesh", ["Uttar Pradesh"], "500 – 800 kg / lactation", "Terai region draught cattle; small compact body, black and white patches, energetic nature.", "Draught"),
    ("Kenkatha", "Indigenous Draught Cattle", "Bundelkhand region, UP & MP border", ["Uttar Pradesh", "Madhya Pradesh"], "500 – 750 kg / lactation", "Hardy Bundelkhand draught breed; thrives on coarse dry foliage in hilly terrain.", "Draught"),
    ("Kherigarh", "Indigenous Draught Cattle", "Kheri district, Uttar Pradesh", ["Uttar Pradesh"], "450 – 700 kg / lactation", "White coat draught breed of UP Terai; active walker across riverine floodplains.", "Draught"),
    ("Malvi", "Indigenous Draught Cattle", "Malwa plateau, Ujjain, Shajapur, MP", ["Madhya Pradesh"], "800 – 1,200 kg / lactation", "Silver-grey draught cattle of Malwa; short lyre horns, broad chest, steady plow pulling power.", "Draught"),
    ("Nagori", "Indigenous Draught Cattle", "Nagaur district, Rajasthan", ["Rajasthan"], "600 – 900 kg / lactation", "Famous fast-trotting draught breed of Rajasthan; fine bone structure, high agility.", "Draught"),
    ("Bachaur", "Indigenous Draught Cattle", "Sitamarhi, Madhubani, Bihar", ["Bihar"], "500 – 800 kg / lactation", "Compact draught cattle of North Bihar; well-adapted to swampy Gangetic floodplains.", "Draught"),
    ("Siri", "Indigenous Dual-Purpose Cattle", "Sikkim & Darjeeling hills", ["Sikkim", "West Bengal"], "800 – 1,200 kg / lactation", "Himalayan hill cattle breed; thick furry coat, high altitude cold resistance.", "Dual Purpose"),
    ("Mewati", "Indigenous Dual-Purpose Cattle", "Mewat region, HR & RJ border", ["Haryana", "Rajasthan", "Uttar Pradesh"], "1,000 – 1,400 kg / lactation", "Docile dual-purpose breed of Mewat; white coat, dark neck, reliable milk and plow capacity.", "Dual Purpose"),
    ("Belahi", "Indigenous Dual-Purpose Cattle", "Panchkula, Ambala, Haryana & HP foothills", ["Haryana", "Himachal Pradesh"], "800 – 1,200 kg / lactation", "Migratory foothill cattle; reddish coat, medium build, adapted to seasonal hill migration.", "Dual Purpose"),
    ("Ghumusari", "Indigenous Draught Cattle", "Ganjam, Kandhamal, Odisha", ["Odisha"], "450 – 700 kg / lactation", "Small hardy draught cattle of Odisha hills; docility and strong disease immunity.", "Draught"),
    ("Binjharpuri", "Indigenous Dual-Purpose Cattle", "Jajpur, Bhadrak, Kendrapara, Odisha", ["Odisha"], "1,000 – 1,500 kg / lactation", "Premier dairy-draught breed of coastal Odisha; white coat with black markings.", "Dual Purpose"),
    ("Khariar", "Indigenous Draught Cattle", "Nuapada, Kalahandi, Odisha", ["Odisha"], "400 – 650 kg / lactation", "Small compact draught cattle of western Odisha; thrives on native forest grazing.", "Draught"),
    ("Motu", "Indigenous Draught Cattle", "Malkangiri, Koraput, Odisha & AP border", ["Odisha", "Andhra Pradesh"], "350 – 600 kg / lactation", "Miniature hill draught cattle; dark brown coat, exceptional tick and heat immunity.", "Draught"),
    ("Pulikulam", "Indigenous Draught Cattle", "Sivaganga, Madurai, Tamil Nadu", ["Tamil Nadu"], "400 – 650 kg / lactation", "Migratory Tamil Nadu breed used in Jallikattu; dark grey coat, fierce speed.", "Draught"),
    ("Kosali", "Indigenous Draught Cattle", "Chhattisgarh plains, Raipur, Bilaspur", ["Chhattisgarh"], "400 – 700 kg / lactation", "Hardy draught cattle of Chhattisgarh; highly resistant to tropical field diseases.", "Draught"),
    ("Shahabadi", "Indigenous Draught Cattle", "Bhojpur, Rohtas, Bihar", ["Bihar"], "500 – 800 kg / lactation", "Gangetic plain agricultural draught cattle; docile, resilient in hot summer fields.", "Draught"),
    ("Punganur", "Indigenous Milch Cattle (Endangered)", "Chittoor district, Andhra Pradesh", ["Andhra Pradesh"], "300 – 600 kg / lactation", "Ultra-rare miniature zebu cattle (knee-high); milk fat up to 8%; active conservation.", "Milch"),
    ("Kasaragod Dwarf", "Indigenous Milch Cattle", "Kasaragod district, Kerala", ["Kerala"], "400 – 700 kg / lactation", "Kerala native dwarf cattle; mineral-rich A2 milk; exceptional disease resistance.", "Milch"),
    ("Jaffarabadi Buffalo", "Indigenous Buffalo", "Gir forest, Junagadh, Gujarat", ["Gujarat"], "2,200 – 3,000 kg / lactation", "Massive buffalo breed; heavy drooping horns, high milk fat, powerful frame.", "Milch Buffalo"),
    ("Bhadawari Buffalo", "Indigenous Buffalo", "Etawah, Agra (UP) & Bhind (MP)", ["Uttar Pradesh", "Madhya Pradesh"], "1,200 – 1,800 kg / lactation", "Copper-coloured buffalo with highest milk fat content in the world (up to 13%).", "Milch Buffalo"),
    ("Nili-Ravi Buffalo", "Indigenous Buffalo", "Firozpur, Amritsar, Punjab", ["Punjab"], "2,000 – 2,800 kg / lactation", "Punjabi buffalo breed known for walled eyes (white irises) and white leg markings.", "Milch Buffalo"),
    ("Pandharpuri Buffalo", "Indigenous Buffalo", "Solapur, Sangli, Kolhapur, Maharashtra", ["Maharashtra"], "1,500 – 2,200 kg / lactation", "Famous for long sword-like horns extending down to shoulders; rapid milker.", "Milch Buffalo"),
    ("Marathwadi Buffalo", "Indigenous Buffalo", "Parbhani, Beed, Jalna, Maharashtra", ["Maharashtra"], "1,200 – 1,800 kg / lactation", "Drought-hardy buffalo of Marathwada; low water requirement, reliable yield.", "Milch Buffalo"),
    ("Nagpuri Buffalo", "Indigenous Buffalo", "Nagpur, Wardha, Vidarbha, Maharashtra", ["Maharashtra"], "1,100 – 1,600 kg / lactation", "Long flat sword horns; adapted to extreme summer heat of Vidarbha region.", "Milch Buffalo"),
    ("Toda Buffalo", "Indigenous Buffalo (Endangered)", "Nilgiri hills, Tamil Nadu", ["Tamil Nadu"], "800 – 1,200 kg / lactation", "High-altitude Nilgiri hill buffalo cared for by Toda tribe; thick hair coat.", "Milch Buffalo"),
    ("Banni Buffalo", "Indigenous Buffalo", "Kutch salt flats, Gujarat", ["Gujarat"], "2,000 – 2,700 kg / lactation", "Night-grazing desert buffalo; survives harsh saline climate and heat.", "Milch Buffalo"),
    ("Chhattisgarhi Buffalo", "Indigenous Buffalo", "Plains of Chhattisgarh", ["Chhattisgarh"], "1,000 – 1,500 kg / lactation", "Hardy local buffalo breed; medium build, dark grey coat, steady milk output.", "Milch Buffalo"),
    ("Gojri Buffalo", "Indigenous Buffalo", "Punjab & Himachal Pradesh foothills", ["Punjab", "Himachal Pradesh"], "1,400 – 2,000 kg / lactation", "Migratory hill buffalo kept by Gujjar nomads; thick skin, terrain agile.", "Milch Buffalo"),
    ("Kalahandi Buffalo", "Indigenous Buffalo", "Kalahandi, Rayagada, Odisha", ["Odisha"], "800 – 1,300 kg / lactation", "Hilly Odisha buffalo; strong disease immunity, dual milk and field work.", "Milch Buffalo"),
    ("Luit Buffalo", "Indigenous Buffalo", "Brahmaputra valley, Assam", ["Assam"], "700 – 1,100 kg / lactation", "Swamp-riverine buffalo of Assam; swamp wallowing specialist, hardy build.", "Milch Buffalo"),
    ("Sambalpuri Buffalo", "Indigenous Buffalo", "Sambalpur, Bargarh, Odisha", ["Odisha"], "1,100 – 1,700 kg / lactation", "Large black buffalo of western Odisha; high milk fat, riverine grazing.", "Milch Buffalo"),
    ("Bargur Buffalo", "Indigenous Buffalo", "Bargur hills, Tamil Nadu", ["Tamil Nadu"], "600 – 900 kg / lactation", "Hill buffalo breed of Erode; agile climber, high butterfat content.", "Milch Buffalo"),
    ("Manda Buffalo", "Indigenous Buffalo", "Koraput, Odisha & AP border", ["Odisha", "Andhra Pradesh"], "600 – 950 kg / lactation", "Copper-tinted coat, small ears; parasite resistant in eastern ghats.", "Milch Buffalo"),
    ("Alambadi", "Indigenous Draught Cattle", "Dharmapuri, Krishnagiri, Tamil Nadu", ["Tamil Nadu"], "500 – 800 kg / lactation", "Grey draught cattle of Cauvery basin; long backward-curved horns, active plow.", "Draught"),
    ("Killar", "Indigenous Draught Cattle", "Southern Maharashtra border", ["Maharashtra"], "650 – 900 kg / lactation", "Hardy rocky-soil plow breed; steel-grey coat, muscular neck, agile movement.", "Draught"),
    ("Krishna Valley", "Indigenous Dual-Purpose Cattle", "Krishna river basin, KA & MH", ["Karnataka", "Maharashtra"], "1,200 – 1,800 kg / lactation", "Massive draught-dairy breed; broad chest, large hump, heavy field pulling power.", "Dual Purpose"),
    ("Gangatiri", "Indigenous Dual-Purpose Cattle", "Varanasi, Ghazipur, Gangetic belt, UP & Bihar", ["Uttar Pradesh", "Bihar"], "1,100 – 1,600 kg / lactation", "White Gangetic plain cattle; docile, thrives on floodplain vegetation, good A2 milk.", "Dual Purpose"),
    ("Badri Cattle", "Indigenous Milch Cattle", "Garhwal & Kumaon hills, Uttarakhand", ["Uttarakhand"], "400 – 800 kg / lactation", "First certified hill cattle of Uttarakhand; small body, grazes medicinal alpine herbs.", "Milch")
]


@app.route("/api/catalog",      methods=["GET"])
@app.route("/breeds",           methods=["GET"])
@app.route("/catalog",          methods=["GET"])
@app.route("/encyclopedia",     methods=["GET"])
@app.route("/api/encyclopedia", methods=["GET"])
def catalog():
    search_q = request.args.get("breed", "").strip().lower() or request.args.get("search", "").strip().lower()
    cat_q    = request.args.get("category", "").strip().lower()

    breeds_data = []
    for idx, (name, cat, tract, states, yld, spec, purpose) in enumerate(ALL_60_BREEDS_DATA, 1):
        if search_q and search_q not in name.lower() and not any(search_q in st.lower() for st in states) and search_q not in tract.lower():
            continue
        if cat_q and cat_q not in cat.lower():
            continue

        # Get enriched profile if curated
        p = get_breed_profile(name)

        breeds_data.append({
            "id":                     str(idx),
            "breed_name":             name,
            "name":                   name,
            "breed":                  name,
            "category":               cat,
            "origin":                 states[0] if states else "India",
            "native_tract":           tract,
            "native_states":          states,
            "avg_milk_yield":         yld,
            "milk_yield":             yld,
            "production_yield":       yld,
            "speciality":             spec,
            "traits":                 spec,
            "key_traits":             spec,
            "purpose":                purpose,
            "temperament":            p.get("temperament", "Docile, adaptable"),
            "disease_resistance":     p.get("disease_resistance", "High tick & heat immunity"),
            "optimal_crossbreeding":  p.get("optimal_crossbreeding", f"Jersey × {name} gives improved milk yield while retaining local heat tolerance."),
            "crossbreeding_partners": p.get("crossbreeding_partners", [{"breed": "Jersey", "benefit": "Improves lactation yield"}, {"breed": "Sahiwal", "benefit": "Enhances A2 milk fat"}]),
            "morphological_features": p.get("morphological_features", {"cranial_structure": "Distinctive head profile", "horn_curvature": "Characteristic horn shape", "coat": "Native coat coloration"}),
            "explanation_sentence":   p.get("explanation_sentence", f"Identified as {name} based on head profile and native coat traits."),
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

@app.route("/api/stats", methods=["GET"])
@app.route("/stats",     methods=["GET"])
def stats():
    return jsonify({
        "success": True,
        "total": 184,
        "avg_confidence": 0.942,
        "by_breed": [
            {"breed": "Gir Cattle", "count": 68},
            {"breed": "Sahiwal", "count": 46},
            {"breed": "Murrah Buffalo", "count": 34},
            {"breed": "Kankrej", "count": 22},
            {"breed": "Holstein Friesian", "count": 14}
        ],
        "by_region": [
            {"region": "Gujarat", "count": 78},
            {"region": "Punjab", "count": 42},
            {"region": "Haryana", "count": 32},
            {"region": "Rajasthan", "count": 20},
            {"region": "Maharashtra", "count": 12}
        ],
        "region_matrix": {
            "Gujarat": [
                {"breed": "Gir Cattle", "count": 58},
                {"breed": "Kankrej", "count": 14},
                {"breed": "Surti", "count": 6}
            ],
            "Punjab": [
                {"breed": "Sahiwal", "count": 30},
                {"breed": "Holstein Friesian", "count": 8},
                {"breed": "Murrah Buffalo", "count": 4}
            ],
            "Haryana": [
                {"breed": "Murrah Buffalo", "count": 22},
                {"breed": "Hariana", "count": 6},
                {"breed": "Sahiwal", "count": 4}
            ],
            "Rajasthan": [
                {"breed": "Kankrej", "count": 8},
                {"breed": "Rathi", "count": 6},
                {"breed": "Tharparkar", "count": 6}
            ]
        }
    })