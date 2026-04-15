-- =============================================================================
-- PetCircle: Update Product Catalogs
-- Safe to re-run: all statements use ON CONFLICT DO UPDATE (upsert).
-- No TRUNCATEs — existing rows are updated in-place.
--
-- Tables updated:
--   product_food       (F001–F025,   25 rows)
--   product_supplement (S001–S116,  111 rows)
--   product_medicines  (SKU-001–SKU-054, 54 rows)
--
-- Prerequisites: migrations 044, 051 must have already created these tables.
-- =============================================================================

BEGIN;

-- =============================================================================
-- 1. PRODUCT_FOOD (F001–F025)
-- =============================================================================

INSERT INTO product_food (
    sku_id, brand_id, brand_name, product_line, life_stage, breed_size,
    pack_size_kg, mrp, discounted_price, condition_tags, breed_tags,
    vet_diet_flag, popularity_rank, monthly_units_sold, price_per_kg,
    in_stock, notes
) VALUES
('F001', 'BR01', 'Royal Canin',        'Hypoallergenic',          'All',   'All',    2,    1690, 1520, 'allergy,skin,hypoallergenic',     'all',         TRUE,  3,  210, 760,  TRUE,  'Prescription range'),
('F002', 'BR01', 'Royal Canin',        'Hypoallergenic',          'All',   'All',    7,    4990, 4490, 'allergy,skin,hypoallergenic',     'all',         TRUE,  1,  420, 641,  TRUE,  'Most popular pack'),
('F003', 'BR01', 'Royal Canin',        'Hypoallergenic',          'All',   'All',    14,   8900, 7990, 'allergy,skin,hypoallergenic',     'all',         TRUE,  4,  85,  571,  TRUE,  'Value pack'),
('F004', 'BR01', 'Royal Canin',        'Labrador Adult',          'Adult', 'Large',  3,    2100, 1890, 'joint,weight',                    'labrador',    FALSE, 2,  310, 630,  FALSE, 'Breed-specific'),
('F005', 'BR01', 'Royal Canin',        'Labrador Adult',          'Adult', 'Large',  12,   7200, 6480, 'joint,weight',                    'labrador',    FALSE, 5,  90,  540,  FALSE, NULL),
('F006', 'BR01', 'Royal Canin',        'Large Adult',             'Adult', 'Large',  4,    2400, 2160, 'joint,digestive',                 'large_breed', FALSE, 6,  180, 540,  FALSE, NULL),
('F007', 'BR01', 'Royal Canin',        'Large Puppy',             'Puppy', 'Large',  4,    2600, 2340, 'growth',                          'large_breed', FALSE, 7,  150, 585,  FALSE, NULL),
('F008', 'BR01', 'Royal Canin',        'Renal',                   'All',   'All',    2,    2100, 1890, 'kidney,renal',                    'all',         TRUE,  8,  45,  945,  TRUE,  'Prescription'),
('F009', 'BR01', 'Royal Canin',        'Renal',                   'All',   'All',    7,    6500, 5850, 'kidney,renal',                    'all',         TRUE,  9,  30,  836,  TRUE,  NULL),
('F010', 'BR01', 'Royal Canin',        'Gastrointestinal',        'All',   'All',    2,    2200, 1980, 'digestive,IBD,gastrointestinal',  'all',         TRUE,  10, 60,  990,  TRUE,  NULL),
('F011', 'BR02', 'Hills Science Diet', 'i/d Digestive',           'All',   'All',    1.5,  1800, 1620, 'digestive,IBD',                   'all',         TRUE,  11, 55,  1080, TRUE,  NULL),
('F012', 'BR02', 'Hills Science Diet', 'k/d Kidney Care',         'All',   'All',    1.5,  2100, 1890, 'kidney,renal',                    'all',         TRUE,  12, 40,  1260, TRUE,  'Prescription renal'),
('F013', 'BR02', 'Hills Science Diet', 'z/d Allergy',             'All',   'All',    3.5,  4200, 3780, 'allergy,skin',                    'all',         TRUE,  13, 35,  1080, TRUE,  NULL),
('F014', 'BR02', 'Hills Science Diet', 'Large Breed Adult',       'Adult', 'Large',  6,    3800, 3420, 'joint',                           'large_breed', FALSE, 14, 120, 570,  FALSE, NULL),
('F015', 'BR02', 'Hills Science Diet', 'Large Breed Puppy',       'Puppy', 'Large',  6,    4100, 3690, 'growth',                          'large_breed', FALSE, 15, 95,  615,  TRUE,  NULL),
('F016', 'BR03', 'Drools',             'Focus Adult Large',       'Adult', 'Large',  3,    1200, 1080, 'joint',                           'large_breed', FALSE, 16, 380, 360,  TRUE,  'Value India brand'),
('F017', 'BR03', 'Drools',             'Focus Adult Large',       'Adult', 'Large',  12,   4200, 3780, 'joint',                           'large_breed', FALSE, 17, 160, 315,  TRUE,  NULL),
('F018', 'BR03', 'Drools',             'Focus Puppy Large',       'Puppy', 'Large',  3,    1350, 1215, 'growth',                          'large_breed', FALSE, 18, 290, 405,  TRUE,  NULL),
('F019', 'BR03', 'Drools',             'Absolute Calcium',        'Puppy', 'All',    3,    1100, 990,  'growth,bone',                     'all',         FALSE, 19, 210, 330,  TRUE,  NULL),
('F020', 'BR04', 'Pedigree',           'Adult',                   'Adult', 'All',    10,   2200, 1980, NULL,                              'all',         FALSE, 20, 850, 198,  TRUE,  'Mass market'),
('F021', 'BR04', 'Pedigree',           'Puppy',                   'Puppy', 'All',    3,    750,  675,  'growth',                          'all',         FALSE, 21, 620, 225,  TRUE,  NULL),
('F022', 'BR05', 'Farmina N&D',        'GF Ancestral Grain Boar', 'Adult', 'Medium', 3,    3900, 3510, 'skin,coat,grain_free',            'all',         FALSE, 22, 70,  1170, TRUE,  'Premium grain-free'),
('F023', 'BR05', 'Farmina N&D',        'Ocean Cod Puppy',         'Puppy', 'All',    2.5,  3200, 2880, 'growth,skin',                     'all',         FALSE, 23, 45,  1152, TRUE,  NULL),
('F024', 'BR06', 'Acana',              'Regionals Meadowland',    'Adult', 'All',    2,    3500, 3150, 'skin,coat',                       'all',         FALSE, 24, 30,  1575, TRUE,  'Super-premium import'),
('F025', 'BR01', 'Royal Canin',        'Satiety Weight Mgmt',     'All',   'All',    1.5,  1900, 1710, 'obesity,weight',                  'all',         TRUE,  25, 65,  1140, TRUE,  'Prescription weight')
ON CONFLICT (sku_id) DO UPDATE SET
    brand_id           = EXCLUDED.brand_id,
    brand_name         = EXCLUDED.brand_name,
    product_line       = EXCLUDED.product_line,
    life_stage         = EXCLUDED.life_stage,
    breed_size         = EXCLUDED.breed_size,
    pack_size_kg       = EXCLUDED.pack_size_kg,
    mrp                = EXCLUDED.mrp,
    discounted_price   = EXCLUDED.discounted_price,
    condition_tags     = EXCLUDED.condition_tags,
    breed_tags         = EXCLUDED.breed_tags,
    vet_diet_flag      = EXCLUDED.vet_diet_flag,
    popularity_rank    = EXCLUDED.popularity_rank,
    monthly_units_sold = EXCLUDED.monthly_units_sold,
    price_per_kg       = EXCLUDED.price_per_kg,
    in_stock           = EXCLUDED.in_stock,
    notes              = EXCLUDED.notes,
    active             = TRUE;

DO $$
DECLARE c INTEGER;
BEGIN
    SELECT COUNT(*) INTO c FROM product_food;
    RAISE NOTICE 'product_food rows after upsert: %', c;
END $$;


-- =============================================================================
-- 2. PRODUCT_SUPPLEMENT (S001–S116)
-- =============================================================================

INSERT INTO product_supplement (
    sku_id, brand_id, brand_name, product_name, type, form, pack_size,
    mrp, discounted_price, key_ingredients, condition_tags, life_stage_tags,
    popularity_rank, monthly_units, price_per_unit, in_stock, notes
) VALUES

-- ── Original catalog S001–S016 ────────────────────────────────────────────
('S001', 'SB01', 'Honst',       'Fish Oil - Salmon 300ml',    'fish_oil',           'liquid', '300 ml',    850,  765,  'Omega',         'coat,skin,joint,inflammation,omega3', 'adult,puppy',        1,  340, 765,  TRUE,  NULL),
('S002', 'SB01', 'Honst',       'Fish Oil - Salmon 150ml',    'fish_oil',           'liquid', '150 ml',    499,  449,  'Fish Oil',      'coat,skin,joint,omega3',              'adult,puppy',        2,  510, 449,  TRUE,  'Starter size'),
('S003', 'SB02', 'Zesty Paws',  'Omega Bites - 90 chews',     'fish_oil',           'chew',   '90 chews',  1800, 1620, 'UC-II & Zinc',  'coat,skin,omega3',                    'adult',              3,  180, 1620, TRUE,  'Chew form'),
('S004', 'SB02', 'Zesty Paws',  'Mobility Bites - 90 chews',  'joint_supplement',   'chew',   '90 chews',  2100, 1890, NULL,            'joint,hip,arthritis',                 'senior,adult',       4,  145, 1890, FALSE, 'Glucosamine + Chondroitin'),
('S005', 'SB02', 'Zesty Paws',  'Multivitamin Bites - 90',    'multivitamin',       'chew',   '90 chews',  1600, 1440, NULL,            'immunity,general_health',             'adult,puppy',        5,  220, 1440, FALSE, NULL),
('S006', 'SB03', 'Beaphar',     'Puppy Milk',                 'milk_replacer',      'powder', '500 g',     900,  810,  NULL,            'growth,nutrition',                    'puppy',              6,  90,  810,  FALSE, 'For puppies < 6 weeks'),
('S007', 'SB03', 'Beaphar',     'Multivitamin Syrup',         'multivitamin',       'liquid', '200 ml',    650,  585,  NULL,            'immunity,general_health',             'adult,puppy,senior', 7,  210, 585,  FALSE, NULL),
('S008', 'SB04', 'Drools',      'Absolute Boneup - 500g',     'joint_supplement',   'powder', '500 g',     750,  675,  NULL,            'joint,bone',                          'senior,large_breed', 8,  320, 675,  TRUE,  'Calcium + Phosphorus'),
('S009', 'SB05', 'Himalaya',    'Erina EP Coat Supplement',   'coat_supplement',    'liquid', '200 ml',    280,  252,  NULL,            'coat,skin',                           'adult',              9,  480, 252,  TRUE,  'Affordable India brand'),
('S010', 'SB06', 'NutriVet',    'Joint Health Chews - 60',    'joint_supplement',   'chew',   '60 chews',  1400, 1260, NULL,            'joint,hip',                           'senior',             10, 95,  1260, TRUE,  NULL),
('S011', 'SB07', 'Virbac',      'Megaderm - 250 ml',          'skin_supplement',    'liquid', '250 ml',    1100, 990,  NULL,            'skin,allergy,coat,omega6',            'adult',              11, 75,  990,  TRUE,  'Dermatology-grade'),
('S012', 'SB07', 'Virbac',      'Pronefra - 180 ml',          'kidney_supplement',  'liquid', '180 ml',    1800, 1620, NULL,            'kidney,renal',                        'adult,senior',       12, 30,  1620, TRUE,  'Vet-grade phosphate binder'),
('S013', 'SB08', 'Vet Activ',   'Probiotic Paste - 30g',      'probiotic',          'paste',  '30 g',      750,  675,  NULL,            'digestive,gut_health',                'adult,puppy,senior', 13, 165, 675,  TRUE,  NULL),
('S014', 'SB08', 'Vet Activ',   'Urinary Care - 100 tabs',    'urinary_supplement', 'tablet', '100 tabs',  1200, 1080, NULL,            'urinary,bladder',                     'adult',              14, 55,  1080, FALSE, 'D-mannose + cranberry'),
('S015', 'SB09', 'Venkys',      'Gro Pet - 500g',             'growth_supplement',  'powder', '500 g',     650,  585,  NULL,            'growth,bone',                         'puppy',              15, 190, 585,  TRUE,  'Value puppy supplement'),
('S016', 'SB10', 'Pet Health',  'CBD Calming Chews - 30',     'calming',            'chew',   '30 chews',  2200, 1980, NULL,            'anxiety,stress,behaviour',            'adult,senior',       16, 40,  1980, TRUE,  'New category'),

-- ── MyBeau (SB11) S017–S026 ───────────────────────────────────────────────
('S017', 'SB11', 'MyBeau', 'MyBeau Dog Vitamin & Mineral – 150 ml',
  'multivitamin', 'liquid', '150 ml', 850, 765,
  'Omega 3 & 6, Vitamins A D E B-complex',
  'immunity,general_health,skin,coat', 'adult,puppy',
  17, NULL, 765, TRUE, 'B53; 99.5% absorption rate'),

('S018', 'SB11', 'MyBeau', 'MyBeau Dog Vitamin & Mineral – 300 ml',
  'multivitamin', 'liquid', '300 ml', 1375, 1238,
  'Omega 3 & 6, Vitamins A D E B-complex',
  'immunity,general_health,skin,coat', 'adult,puppy',
  18, NULL, 1238, TRUE, 'B17'),

('S019', 'SB11', 'MyBeau', 'MyBeau Dog Vitamin & Mineral – 1.5 L',
  'multivitamin', 'liquid', '1.5 L', 5300, 4770,
  'Omega 3 & 6, Vitamins A D E B-complex',
  'immunity,general_health,skin,coat', 'adult,puppy',
  19, NULL, 4770, TRUE, 'B18; value size'),

('S020', 'SB11', 'MyBeau', 'MyBeau Cat Vitamin & Mineral – 150 ml',
  'multivitamin', 'liquid', '150 ml', 850, 765,
  'Omega 3 & 6, Vitamins A D E B-complex',
  'immunity,general_health,skin,coat', 'adult,kitten',
  20, NULL, 765, TRUE, 'B16'),

('S021', 'SB11', 'MyBeau', 'MyBeau Cat Vitamin & Mineral – 300 ml',
  'multivitamin', 'liquid', '300 ml', 1375, 1238,
  'Omega 3 & 6, Vitamins A D E B-complex',
  'immunity,general_health,skin,coat', 'adult,kitten',
  21, NULL, 1238, TRUE, 'B19'),

('S022', 'SB11', 'MyBeau', 'MyBeau Bone & Joint – 150 ml',
  'joint_supplement', 'liquid', '150 ml', 1100, 990,
  'Omega 3 & 6, Glucosamine, Chondroitin, NZ Green-lipped Mussel',
  'joint,bone,hip', 'adult,senior',
  22, NULL, 990, TRUE, 'B59'),

('S023', 'SB11', 'MyBeau', 'MyBeau Bone & Joint – 300 ml',
  'joint_supplement', 'liquid', '300 ml', 2050, 1845,
  'Omega 3 & 6, Glucosamine, Chondroitin, NZ Green-lipped Mussel',
  'joint,bone,hip', 'adult,senior',
  23, NULL, 1845, TRUE, 'B22'),

('S024', 'SB11', 'MyBeau', 'MyBeau Vision & Optics – 300 ml',
  'eye_supplement', 'liquid', '300 ml', 2025, 1823,
  'Omega 3 6 9 EPA DHA, Astaxanthin, Lutein, CoQ10',
  'eye,vision,antioxidant', 'adult',
  24, NULL, 1823, TRUE, 'B51'),

('S025', 'SB11', 'MyBeau', 'MyBeau Skin & Hair – 300 ml',
  'skin_supplement', 'liquid', '300 ml', 2025, 1823,
  'Omega 3 & 6, Vitamins A D E B-complex',
  'skin,coat,allergy,shedding', 'adult',
  25, NULL, 1823, TRUE, 'B50'),

('S026', 'SB11', 'MyBeau', 'MyBeau Dental & Breath – 300 ml',
  'dental_supplement', 'liquid', '300 ml', 2025, 1823,
  'Omega 3 & 6, Ascophyllum, Celery Oil, Aloe Vera',
  'dental,breath,plaque,tartar', 'adult',
  26, NULL, 1823, TRUE, 'B49'),

-- ── REX (SB12) S027–S031 ─────────────────────────────────────────────────
('S027', 'SB12', 'REX', 'REX 100% Wheat Germ Oil – 20 ml',
  'coat_supplement', 'liquid', '20 ml', 70, 63,
  'Wheat Germ Oil, Natural Vitamin E, EFAs',
  'coat,skin,general_health', 'adult,puppy',
  27, NULL, 63, TRUE, 'B46'),

('S028', 'SB12', 'REX', 'REX 100% Wheat Germ Oil – 100 ml',
  'coat_supplement', 'liquid', '100 ml', 195, 176,
  'Wheat Germ Oil, Natural Vitamin E, EFAs',
  'coat,skin,general_health', 'adult,puppy',
  28, NULL, 176, TRUE, 'B60'),

('S029', 'SB12', 'REX', 'REX 100% Wheat Germ Oil – 250 ml',
  'coat_supplement', 'liquid', '250 ml', 475, 428,
  'Wheat Germ Oil, Natural Vitamin E, EFAs',
  'coat,skin,general_health', 'adult,puppy',
  29, NULL, 428, TRUE, 'B61'),

('S030', 'SB12', 'REX', 'REX 100% Wheat Germ Oil – 500 ml',
  'coat_supplement', 'liquid', '500 ml', 900, 810,
  'Wheat Germ Oil, Natural Vitamin E, EFAs',
  'coat,skin,general_health', 'adult,puppy',
  30, NULL, 810, TRUE, 'B62'),

('S031', 'SB12', 'REX', 'REX 100% Wheat Germ Oil – 1 L',
  'coat_supplement', 'liquid', '1 L', 1675, 1508,
  'Wheat Germ Oil, Natural Vitamin E, EFAs',
  'coat,skin,general_health', 'adult,puppy',
  31, NULL, 1508, TRUE, 'B63; value size'),

-- ── ProDen (SB13) S032–S034 ──────────────────────────────────────────────
('S032', 'SB13', 'ProDen', 'PlaqueOff Powder for Dogs – 20 g',
  'dental_supplement', 'powder', '20 g', 1250, 1125,
  'Seaweed (Ascophyllum nodosum)',
  'dental,breath,plaque,tartar', 'adult,puppy',
  32, NULL, 1125, TRUE, 'B58; sprinkle on food'),

('S033', 'SB13', 'ProDen', 'PlaqueOff Powder for Dogs – 40 g',
  'dental_supplement', 'powder', '40 g', 2150, 1935,
  'Seaweed (Ascophyllum nodosum)',
  'dental,breath,plaque,tartar', 'adult,puppy',
  33, NULL, 1935, TRUE, 'B47'),

('S034', 'SB13', 'ProDen', 'PlaqueOff Powder for Cats – 20 g',
  'dental_supplement', 'powder', '20 g', 1100, 990,
  'Seaweed (Ascophyllum nodosum)',
  'dental,breath,plaque,tartar', 'adult,kitten',
  34, NULL, 990, TRUE, 'FP0502'),

-- ── Ektek Global (SB14) S035–S071 ────────────────────────────────────────
('S035', 'SB14', 'Ektek Global', 'Pet-O-Lac Puppy Milk Formula – 400 g',
  'milk_replacer', 'powder', '400 g', 1100, 990,
  'Milk derivatives, EFAs, Vitamins A D3',
  'growth,nutrition', 'puppy,newborn',
  35, NULL, 990, TRUE, 'Orphan puppies & kittens; Stage 2'),

('S036', 'SB14', 'Ektek Global', 'Bully''s Best Power Gain – 500 g',
  'performance_supplement', 'powder', '500 g', 1100, 990,
  'Creatine Monohydrate',
  'stamina,performance,muscle', 'adult',
  36, NULL, 990, TRUE, 'Sports/working dogs; not for puppies'),

('S037', 'SB14', 'Ektek Global', 'Pet-O-Boost Powder – 250 g',
  'growth_supplement', 'powder', '250 g', 1100, 990,
  'Whey, Vitamins A D B-complex',
  'growth,weight_gain,nutrition', 'puppy,adult',
  37, NULL, 990, TRUE, 'Weight gain; energy boost'),

('S038', 'SB14', 'Ektek Global', 'Pet-O-Boost Powder – 500 g',
  'growth_supplement', 'powder', '500 g', 1100, 990,
  'Whey, Vitamins A D B-complex',
  'growth,weight_gain,nutrition', 'puppy,adult',
  38, NULL, 990, TRUE, 'Value pack'),

('S039', 'SB14', 'Ektek Global', 'Calcishell Pet Calcium Supplement – 500 g',
  'calcium_supplement', 'powder', '500 g', 1100, 990,
  'Calcium, Phosphorus, Magnesium',
  'bone,teeth,growth', 'puppy,adult,senior',
  39, NULL, 990, TRUE, 'Also for pregnant/lactating'),

('S040', 'SB14', 'Ektek Global', 'Grain-Ex Coat Supplement – 500 g',
  'coat_supplement', 'powder', '500 g', 1100, 990,
  'Omega 3 & 6, Ginseng, Spirulina',
  'coat,skin,shedding,allergy', 'adult,puppy',
  40, NULL, 990, TRUE, 'Grain-free; 33 ingredients'),

('S041', 'SB14', 'Ektek Global', 'Pet-O-Coat Syrup – 200 ml',
  'coat_supplement', 'liquid', '200 ml', 1100, 990,
  'Omega 3 & 6, Biotin, Vitamins B-complex',
  'coat,skin,shedding', 'adult,puppy',
  41, NULL, 990, TRUE, 'Skin & coat'),

('S042', 'SB14', 'Ektek Global', 'Pet-O-Coat Syrup – 450 ml',
  'coat_supplement', 'liquid', '450 ml', 1100, 990,
  'Omega 3 & 6, Biotin, Vitamins B-complex',
  'coat,skin,shedding', 'adult,puppy',
  42, NULL, 990, TRUE, 'Value pack'),

('S043', 'SB14', 'Ektek Global', 'Pet-O-Cal Syrup – 200 ml',
  'calcium_supplement', 'liquid', '200 ml', 1100, 990,
  'Calcium, Phosphorus, Vitamin D3, B12',
  'bone,teeth,pregnancy', 'puppy,adult,senior',
  43, NULL, 990, TRUE, 'Calcium + Phosphorus liquid'),

('S044', 'SB14', 'Ektek Global', 'Pet-O-Cal Syrup – 450 ml',
  'calcium_supplement', 'liquid', '450 ml', 1100, 990,
  'Calcium, Phosphorus, Vitamin D3, B12',
  'bone,teeth,pregnancy', 'puppy,adult,senior',
  44, NULL, 990, TRUE, 'Value pack'),

('S045', 'SB14', 'Ektek Global', 'Multitek Pet Syrup – 200 ml',
  'multivitamin', 'liquid', '200 ml', 1100, 990,
  'Vitamins A D3 E B-complex, Taurine, Amino acids',
  'immunity,general_health,recovery', 'adult,puppy,senior',
  45, NULL, 990, TRUE, 'General multivitamin'),

('S046', 'SB14', 'Ektek Global', 'Ferrimin Iron Tonic Syrup – 200 ml',
  'iron_supplement', 'liquid', '200 ml', 1100, 990,
  'Iron, Vitamin B12, B-complex, Minerals',
  'anemia,immunity,liver', 'adult,puppy,senior',
  46, NULL, 990, TRUE, 'Iron-rich; for sporting & older dogs'),

('S047', 'SB14', 'Ektek Global', 'Pet-O-Cal Tablet – 60 tabs',
  'calcium_supplement', 'tablet', '60 tabs', 1100, 990,
  'Calcium, Phosphorus, Vitamin D3',
  'bone,teeth,immunity', 'puppy,adult,senior',
  47, NULL, 990, TRUE, 'Chewable tablet'),

('S048', 'SB14', 'Ektek Global', 'Pet-O-Vitab Plus Multivitamin – 60 tabs',
  'multivitamin', 'tablet', '60 tabs', 1100, 990,
  'Full amino acid profile, Vitamins A D3 E B-complex, Minerals',
  'immunity,general_health', 'adult,puppy,senior',
  48, NULL, 990, TRUE, 'Full-spectrum multi'),

('S049', 'SB14', 'Ektek Global', 'CoatX Skin & Coat Supplement – 300 ml',
  'coat_supplement', 'liquid', '300 ml', 1100, 990,
  'Omega 3 6 9, MSM, Vitamins, Minerals',
  'coat,skin,shedding', 'adult,puppy',
  49, NULL, 990, TRUE, 'Human-grade ingredients'),

('S050', 'SB14', 'Ektek Global', 'Pet-O-Coat Plus Fatty Acid Tablet – 60 tabs',
  'coat_supplement', 'tablet', '60 tabs', 1100, 990,
  'Marine Lipid, Flaxseed Oil, Omega 3 6, Vitamins',
  'coat,skin,shedding', 'adult,puppy',
  50, NULL, 990, TRUE, 'EFA tablet'),

('S051', 'SB14', 'Ektek Global', 'K-9 Pre+Probiotics Powder – 100 g',
  'probiotic', 'powder', '100 g', 1100, 990,
  'Lactobacillus complex, FOS, Enzyme blend',
  'digestive,gut_health,immunity', 'adult,puppy,senior',
  51, NULL, 990, TRUE, 'Prebiotic + probiotic'),

('S052', 'SB14', 'Ektek Global', 'K-9 Allergy Aid – 100 g',
  'allergy_supplement', 'powder', '100 g', 1100, 990,
  'Colostrum, Turmeric, Salmon Oil, Vitamin C, Licorice',
  'allergy,immunity,skin', 'adult',
  52, NULL, 990, TRUE, 'Anti-oxidative + anti-inflammatory'),

('S053', 'SB14', 'Ektek Global', 'K-9 Eye Support – 100 g',
  'eye_supplement', 'powder', '100 g', 1100, 990,
  'Herbal eye support blend',
  'eye,vision', 'adult',
  53, NULL, 990, TRUE, 'Ocular health powder'),

('S054', 'SB14', 'Ektek Global', 'F-9 Pre+Probiotics for Cats',
  'probiotic', 'powder', '100 g', 1100, 990,
  'Lactobacillus complex, FOS, Enzyme blend',
  'digestive,gut_health,immunity', 'adult,kitten,senior',
  54, NULL, 990, TRUE, 'Cat probiotic'),

('S055', 'SB14', 'Ektek Global', 'F-9 Hairball Tablets – 60 tabs',
  'hairball_supplement', 'tablet', '60 tabs', 1100, 990,
  'Psyllium husk, Marshmallow root, Slippery Elm, Enzyme blend',
  'hairball,digestive', 'adult,kitten',
  55, NULL, 990, TRUE, 'Cat hairball control'),

('S056', 'SB14', 'Ektek Global', 'Poop-Repel Coprophagia Tablet – 30 tabs',
  'behaviour_supplement', 'tablet', '30 tabs', 1100, 990,
  'Proprietary blend',
  'coprophagia,behaviour', 'puppy,adult',
  56, NULL, 990, TRUE, 'From 12 weeks age'),

('S057', 'SB14', 'Ektek Global', 'Poop Firm Stool Aid Tablet – 30 tabs',
  'digestive_supplement', 'tablet', '30 tabs', 1100, 990,
  'Pectin, Prebiotic fibre',
  'digestive,loose_stool', 'adult,puppy',
  57, NULL, 990, TRUE, 'Stool firmer with pectin'),

('S058', 'SB14', 'Ektek Global', 'Thyro Mania G Thyroid Support Drops',
  'thyroid_supplement', 'drops', 'drops', 1100, 990,
  'Herbal thyroid blend',
  'thyroid,metabolic,weight', 'adult,senior',
  58, NULL, 990, TRUE, 'For cats & dogs; hyperthyroidism'),

('S059', 'SB14', 'Ektek Global', 'Domicart Hip & Joint Support Drops',
  'joint_supplement', 'drops', 'drops', 1100, 990,
  'Herbal joint blend',
  'joint,hip,arthritis', 'adult,senior',
  59, NULL, 990, TRUE, 'Hip dysplasia support'),

('S060', 'SB14', 'Ektek Global', 'CardioCip Pet Cardiac Tablet – 60 tabs',
  'cardiac_supplement', 'tablet', '60 tabs', 1100, 990,
  'Terminalia arjuna, Ginger, Turmeric, Garlic',
  'cardiac,heart', 'adult,senior',
  60, NULL, 990, TRUE, 'Herbal cardiovascular'),

('S061', 'SB14', 'Ektek Global', 'Easy Breathe Respiratory Drops – 60 ml',
  'respiratory_supplement', 'drops', '60 ml', 1100, 990,
  'Marshmallow root, Holy basil, Curcuma longa',
  'respiratory,cough,wheeze', 'adult,puppy',
  61, NULL, 990, TRUE, 'Ayurveda herbal drops'),

('S062', 'SB14', 'Ektek Global', 'Hemp-O-Tek Calming Drops – 60 ml',
  'calming', 'drops', '60 ml', 1100, 990,
  'Hemp Oil, herbal calming blend',
  'anxiety,stress,behaviour', 'adult,senior',
  62, NULL, 990, TRUE, 'Anxiety relief enriched with hemp oil'),

('S063', 'SB14', 'Ektek Global', 'Diabecip Diabetes Support Syrup – 200 ml',
  'metabolic_supplement', 'liquid', '200 ml', 1100, 990,
  'Karela, Gurmar, Jamun, Methi, Ashwagandha',
  'diabetes,metabolic,immunity', 'adult,senior',
  63, NULL, 990, TRUE, 'Ayurveda; diabetes companion'),

('S064', 'SB14', 'Ektek Global', 'PetCurin Antioxidant Suspension – 200 ml',
  'antioxidant_supplement', 'liquid', '200 ml', 1100, 990,
  'Curcumin 95%, Piperine 95%',
  'antioxidant,immunity,inflammation', 'adult,puppy,senior',
  64, NULL, 990, TRUE, 'Antiviral, antibacterial, anti-cancer'),

('S065', 'SB14', 'Ektek Global', 'Pet-O-Liv Liver Tonic Syrup – 200 ml',
  'liver_supplement', 'liquid', '200 ml', 1100, 990,
  'Punarnava, Kasni, Guduchi, Bhui amla, Bhringraj',
  'liver,hepatic,detox', 'adult,puppy,senior',
  65, NULL, 990, TRUE, 'Herbal liver tonic'),

('S066', 'SB14', 'Ektek Global', 'DigipEt Digestive Stimulant Syrup – 200 ml',
  'digestive_supplement', 'liquid', '200 ml', 1100, 990,
  'Pudina, Sonth, Harad, Amla, Jeera, Ajwain',
  'digestive,gut_health,flatulence', 'adult,puppy,senior',
  66, NULL, 990, TRUE, 'Anti-flatulent, bowel regulator'),

('S067', 'SB14', 'Ektek Global', 'Pet-O-Ease Calming & Stress Syrup',
  'calming', 'liquid', '200 ml', 1100, 990,
  'Ashwagandha, Brahmi, Shankhpushpi, Jatamansi',
  'anxiety,stress,behaviour,hyperactivity', 'adult,puppy',
  67, NULL, 990, TRUE, 'Anxiolytic, behaviour modifier'),

('S068', 'SB14', 'Ektek Global', 'DigiSpas Digestive Drops – 30 ml',
  'digestive_supplement', 'drops', '30 ml', 1100, 990,
  'Dill oil, Giloe, Amla, Kasni',
  'digestive,colic,flatulence', 'adult,puppy,kitten',
  68, NULL, 990, TRUE, 'Bowel movement regulator'),

('S069', 'SB14', 'Ektek Global', 'Pet-O-Lact Lactation Booster Syrup – 200 ml',
  'reproductive_supplement', 'liquid', '200 ml', 1100, 990,
  'Shatavar, Tulsi, Fenugreek, Milk Thistle',
  'lactation,nursing', 'adult',
  69, NULL, 990, TRUE, 'Natural lactation booster for nursing females'),

('S070', 'SB14', 'Ektek Global', 'Adinatek Adrenal Support Drops',
  'adrenal_supplement', 'drops', 'drops', 1100, 990,
  'Herbal adrenal support blend',
  'adrenal,cushings,hormonal', 'adult,senior',
  70, NULL, 990, TRUE, 'Cushing''s disease support'),

('S071', 'SB14', 'Ektek Global', 'Platogrow Platelet Enhancer Syrup',
  'immunity_supplement', 'liquid', '200 ml', 1100, 990,
  'Giloy, Papita, Tulsi, Pudina, Apple',
  'platelets,immunity,blood', 'adult',
  71, NULL, 990, TRUE, 'Thrombocytopenia support'),

-- ── Vetina (SB15) S072–S074, S079–S101 ──────────────────────────────────
('S072', 'SB15', 'Vetina', 'Soft Coat Skin & Coat Supplement – 200 ml',
  'coat_supplement', 'liquid', '200 ml', 1100, 990,
  'Omega 6 (3000mg), Omega 3, EPA, DHA, Biotin, Curcumin',
  'coat,skin,allergy,shedding,inflammation', 'adult,puppy',
  72, NULL, 990, TRUE, '0.5ml/kg/day; dogs & cats'),

('S073', 'SB15', 'Vetina', 'Allergia Allergy Relief Tablet – 30 tabs',
  'allergy_supplement', 'tablet', '30 tabs', 1100, 990,
  'Quercetin, Citrus bioflavonoids, Omega 3, Vitamins A C E',
  'allergy,skin,immunity,sneezing', 'adult,puppy',
  73, NULL, 990, TRUE, 'Nature''s Benadryl – Quercetin formula'),

('S074', 'SB15', 'Vetina', 'Omeglo Skin & Joint Supplement – 200 ml',
  'coat_supplement', 'liquid', '200 ml', 1100, 990,
  'Cold-pressed Linseed Oil, Marine Algae Oil, Rice Bran Oil, Vitamins A D3',
  'coat,skin,joint,dermatosis', 'adult,puppy',
  74, NULL, 990, TRUE, 'Ireland origin; complementary dietetic feed'),

('S079', 'SB15', 'Vetina', 'Vetramil Auris Ear Drops – 50 ml',
  'ear_supplement', 'drops', '50 ml', 1100, 990,
  'Honey, Propylene glycol, Polysorbate',
  'ear,otitis,infection', 'adult',
  75, NULL, 990, TRUE, 'Netherlands; with canule'),

('S080', 'SB15', 'Vetina', 'Puppy & Kitten Milk Replacer – 200 g',
  'milk_replacer', 'powder', '200 g', 1100, 990,
  'Whey, Colostrum, Vitamins, Minerals, Probiotics',
  'growth,nutrition,immunity', 'puppy,newborn',
  76, NULL, 990, TRUE, 'Includes feeding bottle; Saccharomyces probiotic'),

('S081', 'SB15', 'Vetina', 'Puppy Serelac Weaning Formula – 400 g',
  'milk_replacer', 'powder', '400 g', 1100, 990,
  'Protein, Colostrum, DHA, Vitamins, Minerals, Amino Acids',
  'growth,nutrition,weaning', 'puppy',
  77, NULL, 990, TRUE, 'Enriched weaning formula; 3-10 weeks'),

('S082', 'SB15', 'Vetina', 'Vet DMG 125 Immune Performance Drops – 15 ml',
  'performance_supplement', 'drops', '15 ml', 1100, 990,
  'N,N-Dimethylglycine (DMG) 125mg/ml',
  'immunity,performance,stamina,liver', 'adult',
  78, NULL, 990, TRUE, 'Twice daily 2 wks then once daily'),

('S083', 'SB15', 'Vetina', 'CaniGel Nutritional Energizing Gel – 120 g',
  'growth_supplement', 'gel', '120 g', 1100, 990,
  'L-Carnitine, Vitamins, Minerals, B-complex',
  'weight_gain,nutrition,recovery', 'puppy,adult',
  79, NULL, 990, TRUE, 'High-calorie; for inappetence & recovery'),

('S084', 'SB15', 'Vetina', 'Well Up Multivitamin Tablet – 30 tabs',
  'multivitamin', 'tablet', '30 tabs', 1100, 990,
  'Vitamins A D3 E B-complex, DL-Methionine, L-Lysine, Taurine, Zinc',
  'immunity,general_health,growth', 'adult,puppy,kitten',
  80, NULL, 990, TRUE, 'All life stages; chelated Zinc'),

('S085', 'SB15', 'Vetina', 'Multiplex Vitamin & Mineral Powder – 200 g',
  'multivitamin', 'powder', '200 g', 1100, 990,
  'Vitamins A D3 E K B-complex, Taurine, Methionine, Choline, Biotin',
  'immunity,general_health', 'adult,puppy,senior',
  81, NULL, 990, TRUE, 'Ireland; complementary feed supplement'),

('S086', 'SB15', 'Vetina', 'Ventrogermina Probiotic Suspension – 10×5 ml',
  'probiotic', 'liquid', '10 x 5 ml', 1100, 990,
  'Bacillus clausii 2 billion spores/5ml',
  'digestive,diarrhea,gut_health', 'adult,puppy,senior',
  82, NULL, 990, TRUE, 'Lactose/sugar/gluten free; antibiotic-associated diarrhea'),

('S087', 'SB15', 'Vetina', 'Canigest Probiotic Paste – 30 ml',
  'probiotic', 'paste', '30 ml', 1100, 990,
  'Enterococcus Faecium, FOS, MOS, Kaolin, Pectin, Glutamine',
  'digestive,gut_health,diarrhea', 'adult,puppy',
  83, NULL, 990, TRUE, 'Ireland; 5-day course'),

('S088', 'SB15', 'Vetina', 'Canigest Combi Probiotic Paste – 32 ml',
  'probiotic', 'paste', '32 ml', 1100, 990,
  'Enterococcus Faecium, Lactobacillus Acidophilus, FOS, Kaolin',
  'digestive,gut_health,diarrhea', 'adult,puppy',
  84, NULL, 990, TRUE, '2 probiotic strains; COMBI formula'),

('S089', 'SB15', 'Vetina', 'Cat Hairball Protector Paste – 60 g',
  'hairball_supplement', 'paste', '60 g', 1100, 990,
  'Malt extract 50.6%, Petrolatum, Psyllium husk, Vitamin E',
  'hairball,digestive', 'adult,kitten',
  85, NULL, 990, TRUE, 'USA; do not use <6 months'),

('S090', 'SB15', 'Vetina', 'Fecal Deterrent Coprophagia Tablet – 30 tabs',
  'behaviour_supplement', 'tablet', '30 tabs', 1100, 990,
  'Monosodium Glutamate, Oleoresin Capsicum',
  'coprophagia,behaviour', 'adult,puppy',
  86, NULL, 990, TRUE, 'Imparts unpleasant taste to stool'),

('S091', 'SB15', 'Vetina', 'Cardio-Support Cardiac Tablet – 30 tabs',
  'cardiac_supplement', 'tablet', '30 tabs', 1100, 990,
  'L-Carnitine, Taurine, Hawthorn extract, CoQ10, Arjuna extract',
  'cardiac,heart', 'adult,senior',
  87, NULL, 990, TRUE, 'Ireland; 30 tab / 10×1×10 tab'),

('S092', 'SB15', 'Vetina', 'Hepa Support Liver Tablet – 30 tabs',
  'liver_supplement', 'tablet', '30 tabs', 1100, 990,
  'L-Methionine, N-Acetyl Cysteine, Milk Thistle, Curcumin, Phosphatidylcholine',
  'liver,hepatic,detox', 'adult,senior',
  88, NULL, 990, TRUE, 'Ireland; Glutathione support'),

('S093', 'SB15', 'Vetina', 'Vetina Urso Tablet 300 mg',
  'liver_supplement', 'tablet', '10×10 tabs', 1100, 990,
  'Ursodeoxycholic Acid 300mg, Silymarin 140mg',
  'liver,hepatic,cholestasis', 'adult,senior',
  89, NULL, 990, TRUE, 'Hepatoprotective; vet-grade'),

('S094', 'SB15', 'Vetina', 'Vetina Urso Suspension 125 mg – 100 ml',
  'liver_supplement', 'liquid', '100 ml', 1100, 990,
  'Ursodeoxycholic Acid 125mg/5ml, Silymarin 50mg/5ml',
  'liver,hepatic,cholestasis', 'adult,senior',
  90, NULL, 990, TRUE, 'Vet-grade; chronic hepatitis'),

('S095', 'SB15', 'Vetina', 'Uro Support Bladder Tablet – 30 tabs',
  'urinary_supplement', 'tablet', '30 tabs', 1100, 990,
  'Pumpkin seed, Cranberry extract, Rehmannia root, Dandelion, Vitamin C',
  'urinary,bladder,incontinence', 'adult,senior',
  91, NULL, 990, TRUE, 'Ireland; bladder muscle support'),

('S096', 'SB15', 'Vetina', 'Furinaid Plus Cystitis Liquid – 200 ml',
  'urinary_supplement', 'liquid', '200 ml', 1100, 990,
  'N-Acetyl Glucosamine, L-Tryptophan',
  'urinary,bladder,cystitis,stress', 'adult',
  92, NULL, 990, TRUE, 'Ireland; idiopathic cystitis support'),

('S097', 'SB15', 'Vetina', 'Stride Plus Joint Supplement – 200 ml',
  'joint_supplement', 'liquid', '200 ml', 1100, 990,
  'Glucosamine HCl, MSM, Chondroitin Sulphate, Sodium Hyaluronate',
  'joint,cartilage,arthritis,mobility', 'adult,senior',
  93, NULL, 990, TRUE, 'Ireland; 200ml pump bottle'),

('S098', 'SB15', 'Vetina', 'Stride Advanced Joint Supplement – 200 ml',
  'joint_supplement', 'liquid', '200 ml', 1100, 990,
  'Glucosamine HCl, Marine Algae Oil, Chondroitin Sulphate, MSM, Hyaluronic Acid',
  'joint,cartilage,arthritis,mobility', 'adult,senior',
  94, NULL, 990, TRUE, 'Ireland; vegan formula; EPA+DHA algae'),

('S099', 'SB15', 'Vetina', 'Stride Advanced Joint Supplement – 500 ml',
  'joint_supplement', 'liquid', '500 ml', 1100, 990,
  'Glucosamine HCl, Marine Algae Oil, Chondroitin Sulphate, MSM, Hyaluronic Acid',
  'joint,cartilage,arthritis,mobility', 'adult,senior',
  95, NULL, 990, TRUE, 'Value pack; vegan formula'),

('S100', 'SB15', 'Vetina', 'Nerve On Nerve Support Tablet – 30 tabs',
  'nerve_supplement', 'tablet', '30 tabs', 1100, 990,
  'Methylcobalamin 500mcg, Alpha Lipoic Acid 100mg, Lycopene, Selenium',
  'nerve,neuropathy,pain', 'adult,senior',
  96, NULL, 990, TRUE, 'Neuroprotective; anti-oxidant'),

('S101', 'SB15', 'Vetina', 'Calm On Calming Tablet – 30 tabs',
  'calming', 'tablet', '30 tabs', 1100, 990,
  'Chamomile 45mg, Valerian root 45mg, Ginger 45mg',
  'anxiety,stress,behaviour,travel', 'adult,senior',
  97, NULL, 990, TRUE, 'Natural; for fireworks/travel/grooming stress'),

-- ── Venkys (SB09) S102–S116 ──────────────────────────────────────────────
('S102', 'SB09', 'Venkys', 'VenCoat Omega 3 & 6 Powder – 200 g',
  'coat_supplement', 'powder', '200 g', 1100, 990,
  'Linoleic Acid, Linolenic Acid, EPA 42.5mg, DHA 27.5mg, Vitamins A D3 E',
  'coat,skin,shedding', 'adult,puppy',
  98, NULL, 990, TRUE, '5g/day; skin, hair coat & general condition'),

('S103', 'SB09', 'Venkys', 'VenCoat Omega 3 & 6 Powder – 450 g',
  'coat_supplement', 'powder', '450 g', 1100, 990,
  'Linoleic Acid, Linolenic Acid, EPA, DHA, Vitamins A D3 E',
  'coat,skin,shedding', 'adult,puppy',
  99, NULL, 990, TRUE, 'Value pack'),

('S104', 'SB09', 'Venkys', 'VenCoat Omega 3 & 6 Liquid with Biotin – 200 g',
  'coat_supplement', 'liquid', '200 g', 1100, 990,
  'Omega 6 6000mg, Omega 3 600mg, Biotin 50mcg per 10g',
  'coat,skin,shedding', 'adult,puppy',
  100, NULL, 990, TRUE, '10g/day; lustrous & shiny coat'),

('S105', 'SB09', 'Venkys', 'VenCal-P Calcium Supplement Syrup – 200 ml',
  'calcium_supplement', 'liquid', '200 ml', 1100, 990,
  'Calcium 100mg, Phosphorus 50mg, Magnesium, Vit D3, Vit B12',
  'bone,teeth,pregnancy,growth', 'puppy,adult,senior',
  101, NULL, 990, TRUE, '5-10ml twice daily'),

('S106', 'SB09', 'Venkys', 'VenCal-P Calcium Supplement Syrup – 1 L',
  'calcium_supplement', 'liquid', '1 L', 1100, 990,
  'Calcium 100mg, Phosphorus 50mg, Magnesium, Vit D3, Vit B12',
  'bone,teeth,pregnancy,growth', 'puppy,adult,senior',
  102, NULL, 990, TRUE, 'Value pack'),

('S107', 'SB09', 'Venkys', 'Ventriliv Pet Liver Stimulant Syrup – 200 ml',
  'liver_supplement', 'liquid', '200 ml', 1100, 990,
  'Silybum marianum, Andrographis, Eclipta alba, Phyllanthus niruri, Choline',
  'liver,hepatic,detox,appetite', 'adult,puppy,senior',
  103, NULL, 990, TRUE, 'Herbal; enriched with choline chloride'),

('S108', 'SB09', 'Venkys', 'Pet Spark Growth & Multivitamin Syrup – 200 ml',
  'growth_supplement', 'liquid', '200 ml', 1100, 990,
  'Amino acids (Lysine Methionine etc), Vitamins A D3 E B-complex, Minerals',
  'growth,nutrition,immunity,breeding', 'adult,puppy',
  104, NULL, 990, TRUE, '10ml twice daily; libido + breeding'),

('S109', 'SB09', 'Venkys', 'VenGro Drops – 20 ml',
  'growth_supplement', 'drops', '20 ml', 1100, 990,
  'Amino acids, DHA, EPA, Taurine, Vitamins A D3 E C B-complex',
  'growth,brain_development,vision', 'puppy,kitten',
  105, NULL, 990, TRUE, 'Paediatric; 0.5-2ml daily'),

('S110', 'SB09', 'Venkys', 'VenGro Syrup – 200 ml',
  'growth_supplement', 'liquid', '200 ml', 1100, 990,
  'Amino acids, DHA, EPA, Taurine, Vitamins A D3 E C B-complex',
  'growth,brain_development,vision', 'puppy,adult',
  106, NULL, 990, TRUE, '5ml twice daily; dogs cats & birds'),

('S111', 'SB09', 'Venkys', 'Fe-folate Iron Supplement Syrup – 200 ml',
  'iron_supplement', 'liquid', '200 ml', 1100, 990,
  'Elemental Iron 50mg, Folic Acid 175mcg, Vitamin B12 per 5ml',
  'anemia,iron_deficiency,blood', 'puppy,adult',
  107, NULL, 990, TRUE, '5ml twice daily; anemia & blood formation'),

('S112', 'SB09', 'Venkys', 'Thromb Beat Platelet Enhancer Syrup – 100 ml',
  'immunity_supplement', 'liquid', '100 ml', 1100, 990,
  'Papaya leaf extract, Tinospora, Withania, Iron, Folic acid',
  'platelets,immunity,tick_fever,blood', 'adult',
  108, NULL, 990, TRUE, 'Thrombocytopenia & tick fever support'),

('S113', 'SB09', 'Venkys', 'Biofit Liver & Kidney Cleanser Syrup – 200 ml',
  'liver_supplement', 'liquid', '200 ml', 1100, 990,
  'Milk thistle, Liquorice, Tribulus, Dandelion, Asparagus',
  'liver,kidney,detox', 'adult',
  109, NULL, 990, TRUE, 'Removes toxins; herbal blend'),

('S114', 'SB09', 'Venkys', 'Venlyte Pet Electrolyte Supplement',
  'electrolyte_supplement', 'powder', 'sachet', 1100, 990,
  'Sodium, Potassium, Vitamin C, Organic nutritive carrier',
  'dehydration,diarrhea,stress', 'adult,puppy',
  110, NULL, 990, TRUE, 'Dissolve in 1L drinking water; 300 mOsmol/L'),

('S115', 'SB09', 'Venkys', 'Gutwell Probiotic Prebiotic Powder – 30 g',
  'probiotic', 'powder', '30 g', 1100, 990,
  'Saccharomyces cerevisiae, Lactobacillus complex, FOS, MOS, Enzyme blend',
  'digestive,gut_health,immunity,hairball', 'adult,puppy,senior',
  111, NULL, 990, TRUE, '800 million CFU + enzyme complex'),

('S116', 'SB09', 'Venkys', 'Ventripro Puppy & Kitten Milk Replacer – 200 g',
  'milk_replacer', 'powder', '200 g', 1100, 990,
  'Protein, Fat, Colostrum, DHA, Calcium, Vitamins, Minerals',
  'growth,nutrition,immunity', 'puppy,newborn',
  112, NULL, 990, TRUE, 'Complete milk replacer; 1:4 dilution')

ON CONFLICT (sku_id) DO UPDATE SET
    brand_id         = EXCLUDED.brand_id,
    brand_name       = EXCLUDED.brand_name,
    product_name     = EXCLUDED.product_name,
    type             = EXCLUDED.type,
    form             = EXCLUDED.form,
    pack_size        = EXCLUDED.pack_size,
    mrp              = EXCLUDED.mrp,
    discounted_price = EXCLUDED.discounted_price,
    key_ingredients  = EXCLUDED.key_ingredients,
    condition_tags   = EXCLUDED.condition_tags,
    life_stage_tags  = EXCLUDED.life_stage_tags,
    popularity_rank  = EXCLUDED.popularity_rank,
    monthly_units    = EXCLUDED.monthly_units,
    price_per_unit   = EXCLUDED.price_per_unit,
    in_stock         = EXCLUDED.in_stock,
    notes            = EXCLUDED.notes,
    active           = TRUE;

DO $$
DECLARE c INTEGER;
BEGIN
    SELECT COUNT(*) INTO c FROM product_supplement;
    RAISE NOTICE 'product_supplement rows after upsert: %', c;
END $$;


-- =============================================================================
-- 3. PRODUCT_MEDICINES (SKU-001–SKU-054)
-- =============================================================================

INSERT INTO product_medicines (
    sku_id, brand_id, brand_name, product_name, type, form, pack_size,
    mrp_paise, discounted_paise, key_ingredients, condition_tags, life_stage_tags,
    active, popularity_rank, monthly_units_sold, price_per_unit_paise, in_stock,
    dosage, repeat_frequency, notes
) VALUES

-- NexGard Spectra (Boehringer) — Combined Tick, Flea, Heartworm & Deworming
('SKU-001', 'BR-001', 'Boehringer', 'NexGard Spectra 2–3.5 kg',   'Tick, Flea & Deworming (Combined)', 'Chewables', 'Box of 1', 60000,  60000,  'Afoxolaner 9mg + Milbemycin Oxime 1.5mg',   'ticks,fleas,heartworm,roundworm,hookworm', 'dog', TRUE, 1,  NULL, 60000,  TRUE, '1 chewable per month',       'Monthly',                          'Min age 8 weeks; Not for cats'),
('SKU-002', 'BR-001', 'Boehringer', 'NexGard Spectra 3.5–7.5 kg', 'Tick, Flea & Deworming (Combined)', 'Chewables', 'Box of 1', 80000,  80000,  'Afoxolaner 19mg + Milbemycin Oxime 3.1mg',  'ticks,fleas,heartworm,roundworm,hookworm', 'dog', TRUE, 2,  NULL, 80000,  TRUE, '1 chewable per month',       'Monthly',                          'Min age 8 weeks'),
('SKU-003', 'BR-001', 'Boehringer', 'NexGard Spectra 7.5–15 kg',  'Tick, Flea & Deworming (Combined)', 'Chewables', 'Box of 1', 110000, 110000, 'Afoxolaner 38mg + Milbemycin Oxime 6.25mg', 'ticks,fleas,heartworm,roundworm,hookworm', 'dog', TRUE, 3,  NULL, 110000, TRUE, '1 chewable per month',       'Monthly',                          'Min age 8 weeks'),
('SKU-004', 'BR-001', 'Boehringer', 'NexGard Spectra 15–30 kg',   'Tick, Flea & Deworming (Combined)', 'Chewables', 'Box of 1', 140000, 140000, 'Afoxolaner 75mg + Milbemycin Oxime 12.5mg', 'ticks,fleas,heartworm,roundworm,hookworm', 'dog', TRUE, 4,  NULL, 140000, TRUE, '1 chewable per month',       'Monthly',                          'Min age 8 weeks'),
('SKU-005', 'BR-001', 'Boehringer', 'NexGard Spectra 30–60 kg',   'Tick, Flea & Deworming (Combined)', 'Chewables', 'Box of 1', 180000, 180000, 'Afoxolaner 150mg + Milbemycin Oxime 25mg',  'ticks,fleas,heartworm,roundworm,hookworm', 'dog', TRUE, 5,  NULL, 180000, TRUE, '1 chewable per month',       'Monthly',                          'Min age 8 weeks; Large breeds'),

-- NexGard (Boehringer) — Tick & Flea only
('SKU-006', 'BR-001', 'Boehringer', 'NexGard 2–4 kg',   'Tick & Flea Protection', 'Chewables', '3 Chewable Tablets', 50000,  50000,  'Afoxolaner 11.3mg', 'ticks,fleas', 'dog', TRUE, 6,  NULL, 16667, TRUE, '1 chewable per month', 'Monthly', 'Min age 8 weeks, min weight 2kg'),
('SKU-007', 'BR-001', 'Boehringer', 'NexGard 4–10 kg',  'Tick & Flea Protection', 'Chewables', '3 Chewable Tablets', 80000,  80000,  'Afoxolaner 28.3mg', 'ticks,fleas', 'dog', TRUE, 7,  NULL, 26667, TRUE, '1 chewable per month', 'Monthly', 'Min age 8 weeks, min weight 4kg'),
('SKU-008', 'BR-001', 'Boehringer', 'NexGard 10–25 kg', 'Tick & Flea Protection', 'Chewables', '3 Chewable Tablets', 120000, 120000, 'Afoxolaner 68mg',   'ticks,fleas', 'dog', TRUE, 8,  NULL, 40000, TRUE, '1 chewable per month', 'Monthly', 'Min age 8 weeks, min weight 10kg'),
('SKU-009', 'BR-001', 'Boehringer', 'NexGard 25–50 kg', 'Tick & Flea Protection', 'Chewables', '3 Chewable Tablets', 160000, 160000, 'Afoxolaner 136mg',  'ticks,fleas', 'dog', TRUE, 9,  NULL, 53333, TRUE, '1 chewable per month', 'Monthly', 'Min age 8 weeks, min weight 25kg; Large breeds'),

-- Broadline (Boehringer) — Spot-on for cats
('SKU-010', 'BR-001', 'Boehringer', 'Broadline <2.5 kg',     'Tick, Flea & Deworming (Combined)', 'Spot-on, pipette', '1 (0.3ml)', 80000,  80000,  'Fipronil 25mg + Methoprene 6.25mg + Eprinomectin 0.5mg + Praziquantel 15mg',  'ticks,fleas,roundworm,hookworm,tapeworm,lungworm,heartworm', 'cat', TRUE, 10, NULL, 80000,  TRUE, '1 pipette per month', 'Monthly', 'For cats <2.5kg; min age 7 weeks'),
('SKU-011', 'BR-001', 'Boehringer', 'Broadline 2.5–7.5 kg',  'Tick, Flea & Deworming (Combined)', 'Spot-on, pipette', '1 (0.9ml)', 120000, 120000, 'Fipronil 50mg + Methoprene 60mg + Eprinomectin 0.5mg + Praziquantel 15mg',   'ticks,fleas,roundworm,hookworm,tapeworm,lungworm,heartworm', 'cat', TRUE, 11, NULL, 120000, TRUE, '1 pipette per month', 'Monthly', 'For cats 2.5–7.5kg; min age 7 weeks'),

-- Frontline Plus (Boehringer) — Spot-on
('SKU-012', 'BR-001', 'Boehringer', 'Frontline Plus 2–10 kg',  'Tick & Flea Protection', 'Spot-on, pipette', '3 pipettes (0.67ml each)', 90000,  90000,  'Fipronil 9.8% + (S)-Methoprene 8.8%', 'ticks,fleas,flea_eggs,flea_larvae', 'dog', TRUE, 12, NULL, 30000, TRUE, 'Apply once per month', 'Monthly', 'Min age 8 weeks; covers 2–10kg'),
('SKU-013', 'BR-001', 'Boehringer', 'Frontline Plus 10–20 kg', 'Tick & Flea Protection', 'Spot-on, pipette', '3 pipettes (1.34ml each)', 130000, 130000, 'Fipronil 9.8% + (S)-Methoprene 8.8%', 'ticks,fleas,flea_eggs,flea_larvae', 'dog', TRUE, 13, NULL, 43333, TRUE, 'Apply once per month', 'Monthly', 'Min age 8 weeks; covers 10–20kg'),
('SKU-014', 'BR-001', 'Boehringer', 'Frontline Plus 20–40 kg', 'Tick & Flea Protection', 'Spot-on, pipette', '3 pipettes (2.68ml each)', 180000, 180000, 'Fipronil 9.8% + (S)-Methoprene 8.8%', 'ticks,fleas,flea_eggs,flea_larvae', 'dog', TRUE, 14, NULL, 60000, TRUE, 'Apply once per month', 'Monthly', 'Min age 8 weeks; covers 20–40kg'),
('SKU-015', 'BR-001', 'Boehringer', 'Frontline Plus Cat',      'Tick & Flea Protection', 'Spot-on, pipette', '3 pipettes (0.5ml each)',  100000, 100000, 'Fipronil 9.8% + (S)-Methoprene 11.8%','ticks,fleas,flea_eggs,flea_larvae', 'cat', TRUE, 15, NULL, 33333, TRUE, 'Apply once per month', 'Monthly', 'Min age 8 weeks; single SKU for all cats'),

-- Drontal Plus (Elanco) — Deworming
('SKU-016', 'BR-002', 'Elanco', 'Drontal Plus Tasty Tablets',  'Deworming', 'Tablets', '17×6 Tablets',  120000, 120000, 'Febantel 150mg + Pyrantel 144mg + Praziquantel 50mg', 'roundworm,hookworm,whipworm,tapeworm', 'dog',        TRUE, 16, NULL, 1176,  TRUE, '1 tablet per 10kg body weight', 'Every 3 months (adults); every 2 weeks till 3 months, monthly 3–6 months', 'Min weight 2kg; tasty beef flavour'),
('SKU-017', 'BR-002', 'Elanco', 'Drontal Puppy Suspension',    'Deworming', 'Syrup',   '1 bottle (20ml)', 80000, 80000,  'Pyrantel 14.4mg/ml + Febantel 15mg/ml',               'roundworm,hookworm',                  'dog-puppy',  TRUE, 17, NULL, 80000, TRUE, '1ml per kg body weight',        'Every 2 weeks till 3 months age; monthly from 3–6 months',                 'For puppies from 2 weeks of age'),

-- Milbemax (Elanco)
('SKU-018', 'BR-002', 'Elanco', 'Milbemax Tablets', 'Deworming', 'Tablets', '24×2 Tablets', 150000, 150000, 'Milbemycin Oxime 12.5mg + Praziquantel 125mg', 'roundworm,hookworm,whipworm,lungworm,eyeworm,heartworm', 'dog', TRUE, 18, NULL, 3125, TRUE, '1 tablet per 25kg body weight', 'Every 3 months', 'Min weight 5kg; also for heartworm prevention'),

-- Advocate (Elanco)
('SKU-019', 'BR-002', 'Elanco', 'Advocate 10–25 kg',     'Flea & Deworming (Combined)', 'Spot-on, pipette', '1 (2.5ml)', 120000, 120000, 'Imidacloprid 10% + Moxidectin 2.5%', 'fleas,heartworm,roundworm,hookworm,whipworm,mange,ear_mites', 'dog', TRUE, 19, NULL, 120000, TRUE, 'Apply once per month', 'Monthly', 'Min age 7 weeks; does NOT cover ticks'),
('SKU-020', 'BR-002', 'Elanco', 'Advocate 25–40 kg',     'Flea & Deworming (Combined)', 'Spot-on, pipette', '1 (4ml)',   180000, 180000, 'Imidacloprid 10% + Moxidectin 2.5%', 'fleas,heartworm,roundworm,hookworm,whipworm,mange,ear_mites', 'dog', TRUE, 20, NULL, 180000, TRUE, 'Apply once per month', 'Monthly', 'Min age 7 weeks; for 25-40kg dogs'),
('SKU-021', 'BR-002', 'Elanco', 'Advocate Cat 4–8 kg',   'Flea & Deworming (Combined)', 'Spot-on, pipette', '1 (0.8ml)', 140000, 140000, 'Imidacloprid 10% + Moxidectin 1%',   'fleas,heartworm,roundworm,hookworm,lungworm,ear_mites',       'cat', TRUE, 21, NULL, 140000, TRUE, 'Apply once per month', 'Monthly', 'Min age 9 weeks; does NOT cover ticks'),

-- Advantix (Elanco) — NOT for cats
('SKU-022', 'BR-002', 'Elanco', 'Advantix 25–40 kg', 'Tick & Flea Protection', 'Spot-on, pipette', '1 (4ml)', 100000, 100000, 'Imidacloprid 10% + Permethrin 50%', 'ticks,fleas,sand_flies,mosquitoes,stable_flies', 'dog', TRUE, 22, NULL, 100000, TRUE, 'Apply once every 2 weeks in high-exposure areas', 'Every 2 weeks (high-exposure); Monthly (standard)', 'TOXIC TO CATS; min age 7 weeks, min weight 1.5kg'),

-- Seresto (Elanco) — Collars
('SKU-023', 'BR-002', 'Elanco', 'Seresto Small (upto 8kg)', 'Tick & Flea Protection', 'Collar', '1 collar', 200000, 200000, 'Imidacloprid 10% + Flumethrin 4.5%', 'ticks,fleas,lice', 'dog', TRUE, 23, NULL, 200000, TRUE, '1 collar, continuous release', '8 months protection per collar', 'Water-resistant; for dogs upto 8kg'),
('SKU-024', 'BR-002', 'Elanco', 'Seresto Large (>8kg)',    'Tick & Flea Protection', 'Collar', '1 collar', 250000, 250000, 'Imidacloprid 10% + Flumethrin 4.5%', 'ticks,fleas,lice', 'dog', TRUE, 24, NULL, 250000, TRUE, '1 collar, continuous release', '8 months protection per collar', 'Water-resistant; for dogs >8kg'),

-- Kiltix (Elanco) — Budget Collar
('SKU-025', 'BR-002', 'Elanco', 'Kiltix Medium (upto 19kg)', 'Tick & Flea Protection', 'Collar', '1 collar', 80000, 80000, 'Propoxur 16% + Flumethrin 1.8%', 'ticks,fleas', 'dog', TRUE, 25, NULL, 80000, TRUE, '1 collar, continuous release', '3 months protection per collar', 'Budget-friendly option'),
('SKU-026', 'BR-002', 'Elanco', 'Kiltix Large (>19kg)',     'Tick & Flea Protection', 'Collar', '1 collar', 90000, 90000, 'Propoxur 16% + Flumethrin 1.8%', 'ticks,fleas', 'dog', TRUE, 26, NULL, 90000, TRUE, '1 collar, continuous release', '3 months protection per collar', 'Budget-friendly option; for dogs >19kg'),

-- Fluracto (Indian brand) — 12-week protection
('SKU-027', 'BR-003', 'Fluracto', 'Fluracto SoftChew 2–4.5 kg',  'Tick & Flea Protection', 'Soft Chew, Chewable', '1', 100000, 100000, 'Fluralaner 56.25mg', 'ticks,fleas', 'dog', TRUE, 27, NULL, 100000, TRUE, '1 chewable every 3 months', 'Every 3 months (12 weeks)', 'Min age 8 weeks, min weight 2kg; Indian brand'),
('SKU-028', 'BR-003', 'Fluracto', 'Fluracto SoftChew 4.5–10 kg', 'Tick & Flea Protection', 'Soft Chew, Chewable', '1', 120000, 120000, 'Fluralaner 112.5mg', 'ticks,fleas', 'dog', TRUE, 28, NULL, 120000, TRUE, '1 chewable every 3 months', 'Every 3 months (12 weeks)', 'Min age 8 weeks'),
('SKU-029', 'BR-003', 'Fluracto', 'Fluracto SoftChew 10–20 kg',  'Tick & Flea Protection', 'Soft Chew, Chewable', '1', 150000, 150000, 'Fluralaner 250mg',   'ticks,fleas', 'dog', TRUE, 29, NULL, 150000, TRUE, '1 chewable every 3 months', 'Every 3 months (12 weeks)', 'Min age 8 weeks'),
('SKU-030', 'BR-003', 'Fluracto', 'Fluracto SoftChew 20–40 kg',  'Tick & Flea Protection', 'Soft Chew, Chewable', '1', 200000, 200000, 'Fluralaner 500mg',   'ticks,fleas', 'dog', TRUE, 30, NULL, 200000, TRUE, '1 chewable every 3 months', 'Every 3 months (12 weeks)', 'Min age 8 weeks'),
('SKU-031', 'BR-003', 'Fluracto', 'Fluracto SoftChew 40–56 kg',  'Tick & Flea Protection', 'Soft Chew, Chewable', '1', 250000, 250000, 'Fluralaner 750mg',   'ticks,fleas', 'dog', TRUE, 31, NULL, 250000, TRUE, '1 chewable every 3 months', 'Every 3 months (12 weeks)', 'Min age 8 weeks; for large breeds'),

-- Bravecto (MSD Animal Health) — 12-week
('SKU-032', 'BR-004', 'MSD Animal Health', 'Bravecto 2–4.5 kg',               'Tick & Flea Protection', 'Chewables',       '1',        80000,  80000,  'Fluralaner 112.5mg', 'ticks,fleas',           'dog', TRUE, 32, NULL, 80000,  TRUE, '1 chewable every 12 weeks', 'Every 3 months (12 weeks)', 'Min age 8 weeks; longest-acting oral flea+tick'),
('SKU-033', 'BR-004', 'MSD Animal Health', 'Bravecto 4.5–10 kg',              'Tick & Flea Protection', 'Chewables',       '1',        120000, 120000, 'Fluralaner 250mg',   'ticks,fleas',           'dog', TRUE, 33, NULL, 120000, TRUE, '1 chewable every 12 weeks', 'Every 3 months (12 weeks)', 'Min age 8 weeks'),
('SKU-034', 'BR-004', 'MSD Animal Health', 'Bravecto 10–20 kg',               'Tick & Flea Protection', 'Chewables',       '1',        150000, 150000, 'Fluralaner 500mg',   'ticks,fleas',           'dog', TRUE, 34, NULL, 150000, TRUE, '1 chewable every 12 weeks', 'Every 3 months (12 weeks)', 'Min age 8 weeks'),
('SKU-035', 'BR-004', 'MSD Animal Health', 'Bravecto 20–40 kg',               'Tick & Flea Protection', 'Chewables',       '1',        200000, 200000, 'Fluralaner 1000mg',  'ticks,fleas',           'dog', TRUE, 35, NULL, 200000, TRUE, '1 chewable every 12 weeks', 'Every 3 months (12 weeks)', 'Min age 8 weeks'),
('SKU-036', 'BR-004', 'MSD Animal Health', 'Bravecto Spot-on Cat 2.8–6.25 kg','Tick & Flea Protection', 'Spot-on, pipette','1 pipette', 120000, 120000, 'Fluralaner 280mg',   'ticks,fleas,ear_mites', 'cat', TRUE, 36, NULL, 120000, TRUE, '1 pipette every 12 weeks',  'Every 3 months (12 weeks)', 'Min age 6 months; also covers ear mites'),

-- Bayrocin (Elanco) — Antibiotic
('SKU-037', 'BR-002', 'Elanco', 'Bayrocin Enrofloxacin 150mg', 'Antibiotic (Bacterial Infections)', 'Tablets', 'Strip of 10 tablets', 120000, 120000, 'Enrofloxacin 150mg', 'skin_infection,uti,respiratory_infection,wound_infection,gi_infection', 'dog,cat', TRUE, 37, NULL, 12000, TRUE, '5mg/kg body weight every 24 hours', '3–5 days course', 'Prescription required; not for ticks/fleas/worms'),

-- Drontal Cat (Elanco)
('SKU-038', 'BR-002', 'Elanco', 'Drontal Cat Deworming', 'Deworming', 'Tablets', 'Strip of 2 tablets', 60000, 60000, 'Pyrantel 230mg + Praziquantel 20mg', 'roundworm,hookworm,tapeworm', 'cat', TRUE, 38, NULL, 30000, TRUE, '1 tablet per 4kg body weight', 'Every 3 months', 'For cats above 6 weeks; not for pregnant cats'),

-- Interceptor Plus (MSD)
('SKU-039', 'BR-004', 'MSD Animal Health', 'Interceptor Plus 2–8 kg', 'Deworming', 'Tablets', 'Box of 6', 120000, 120000, 'Milbemycin Oxime 2.3mg + Praziquantel 22.8mg', 'heartworm,roundworm,hookworm,whipworm,tapeworm', 'dog', TRUE, 39, NULL, 20000, TRUE, '1 tablet monthly', 'Monthly', 'Min age 6 weeks; beef flavoured'),

-- Himalaya Erina EP
('SKU-040', 'BR-005', 'Himalaya', 'Erina EP Tick & Flea Spray', 'Tick & Flea Protection', 'Spray', '200ml bottle', 20000, 20000, 'Permethrin 0.1% + Pyrethrin 0.05%', 'ticks,fleas', 'dog', TRUE, 40, NULL, 20000, TRUE, 'Spray on coat, avoid eyes; repeat as needed', 'Every 7–10 days or as needed', 'OTC; India-made; budget option; not for cats'),

-- Beaphar Collar
('SKU-041', 'BR-006', 'Beaphar', 'Beaphar Tick & Flea Collar Dog', 'Tick & Flea Protection', 'Collar', '1 collar', 60000, 60000, 'Deltamethrin 4%', 'ticks,fleas', 'dog', TRUE, 41, NULL, 60000, TRUE, '1 collar, continuous release', '4 months protection', 'Water-resistant; budget collar option in India'),

-- Panacur (Merck)
('SKU-042', 'BR-007', 'Merck Animal Health', 'Panacur Fenbendazole 10% Suspension', 'Deworming', 'Syrup/Suspension', '250ml bottle', 120000, 120000, 'Fenbendazole 100mg/ml', 'roundworm,hookworm,whipworm,giardia', 'dog', TRUE, 42, NULL, 120000, TRUE, '50mg/kg (0.5ml/kg) once daily for 3–5 days', 'Every 3 months or as per vet', 'Safe for pregnant animals; also treats Giardia'),

-- Milpro (Virbac)
('SKU-043', 'BR-008', 'Virbac', 'Milpro Deworming <5kg',  'Deworming', 'Tablets', '1 strip', 80000,  80000,  'Milbemycin Oxime 2.5mg + Praziquantel 25mg', 'roundworm,hookworm,whipworm,tapeworm,heartworm', 'dog', TRUE, 43, NULL, 80000,  TRUE, '1 tablet per 5kg body weight', 'Every 3 months', 'Min age 2 weeks, min weight 0.5kg'),
('SKU-044', 'BR-008', 'Virbac', 'Milpro Deworming >5kg',  'Deworming', 'Tablets', '1 strip', 100000, 100000, 'Milbemycin Oxime 5mg + Praziquantel 50mg',   'roundworm,hookworm,whipworm,tapeworm,heartworm', 'dog', TRUE, 44, NULL, 100000, TRUE, '1 tablet per 5kg body weight', 'Every 3 months', 'Min age 2 weeks, min weight 5kg'),
('SKU-045', 'BR-008', 'Virbac', 'Milpro Deworming Cat',   'Deworming', 'Tablets', '1 strip', 70000,  70000,  'Milbemycin Oxime 4mg + Praziquantel 10mg',   'roundworm,hookworm,tapeworm,heartworm',          'cat', TRUE, 45, NULL, 70000,  TRUE, '1 tablet per 2kg body weight', 'Every 3 months', 'Min age 6 weeks, min weight 0.5kg'),

-- Effipro (Virbac)
('SKU-046', 'BR-008', 'Virbac', 'Effipro 2–10 kg', 'Tick & Flea Protection', 'Spot-on, pipette', '4 pipettes (0.67ml each)',  80000,  80000,  'Fipronil 9.7%', 'ticks,fleas', 'dog', TRUE, 46, NULL, 20000, TRUE, 'Apply once per month', 'Monthly', 'Min age 8 weeks; fipronil without IGR'),
('SKU-047', 'BR-008', 'Virbac', 'Effipro 10–20 kg','Tick & Flea Protection', 'Spot-on, pipette', '4 pipettes (1.34ml each)', 120000, 120000, 'Fipronil 9.7%', 'ticks,fleas', 'dog', TRUE, 47, NULL, 30000, TRUE, 'Apply once per month', 'Monthly', 'Min age 8 weeks'),
('SKU-048', 'BR-008', 'Virbac', 'Effipro Cat',     'Tick & Flea Protection', 'Spot-on, pipette', '4 pipettes (0.5ml each)',  100000, 100000, 'Fipronil 9.7%', 'ticks,fleas', 'cat', TRUE, 48, NULL, 25000, TRUE, 'Apply once per month', 'Monthly', 'Min age 8 weeks'),

-- Simparica (Zoetis)
('SKU-049', 'BR-009', 'Zoetis', 'Simparica 1.3–2.5 kg', 'Tick & Flea Protection', 'Chewables', 'Box of 3', 100000, 100000, 'Sarolaner 5mg',  'ticks,fleas,mange_demodex,mange_sarcoptes', 'dog', TRUE, 49, NULL, 33333, TRUE, '1 chewable per month', 'Monthly', 'Min age 8 weeks, min weight 1.3kg'),
('SKU-050', 'BR-009', 'Zoetis', 'Simparica 2.5–5 kg',   'Tick & Flea Protection', 'Chewables', 'Box of 3', 130000, 130000, 'Sarolaner 10mg', 'ticks,fleas,mange',                         'dog', TRUE, 50, NULL, 43333, TRUE, '1 chewable per month', 'Monthly', 'Min age 8 weeks'),
('SKU-051', 'BR-009', 'Zoetis', 'Simparica 5–10 kg',    'Tick & Flea Protection', 'Chewables', 'Box of 3', 160000, 160000, 'Sarolaner 20mg', 'ticks,fleas,mange',                         'dog', TRUE, 51, NULL, 53333, TRUE, '1 chewable per month', 'Monthly', 'Min age 8 weeks'),
('SKU-052', 'BR-009', 'Zoetis', 'Simparica 10–20 kg',   'Tick & Flea Protection', 'Chewables', 'Box of 3', 220000, 220000, 'Sarolaner 40mg', 'ticks,fleas,mange',                         'dog', TRUE, 52, NULL, 73333, TRUE, '1 chewable per month', 'Monthly', 'Min age 8 weeks'),

-- Stronghold (Zoetis) — cats, NO tick cover
('SKU-053', 'BR-009', 'Zoetis', 'Stronghold 2.6–7.5 kg Cat', 'Flea & Deworming (Combined)', 'Spot-on, pipette', '3 pipettes (0.75ml each)', 120000, 120000, 'Selamectin 60mg/ml', 'fleas,heartworm,roundworm,hookworm,ear_mites,mange', 'cat', TRUE, 53, NULL, 40000, TRUE, 'Apply once per month', 'Monthly', 'Min age 8 weeks; does NOT cover ticks in cats'),

-- Wormectin Plus (Indian Immunologicals)
('SKU-054', 'BR-010', 'Indian Immunologicals', 'Wormectin Plus Tablets Dog', 'Deworming', 'Tablets', '1 strip', 60000, 60000, 'Ivermectin 6mcg/kg + Praziquantel 5mg/kg', 'roundworm,hookworm,tapeworm,mange_external', 'dog', TRUE, 54, NULL, 60000, TRUE, 'As directed by vet', 'Every 3 months or as per vet', 'Budget dewormer; widely available in India; vet prescription advised')

ON CONFLICT (sku_id) DO UPDATE SET
    brand_id             = EXCLUDED.brand_id,
    brand_name           = EXCLUDED.brand_name,
    product_name         = EXCLUDED.product_name,
    type                 = EXCLUDED.type,
    form                 = EXCLUDED.form,
    pack_size            = EXCLUDED.pack_size,
    mrp_paise            = EXCLUDED.mrp_paise,
    discounted_paise     = EXCLUDED.discounted_paise,
    key_ingredients      = EXCLUDED.key_ingredients,
    condition_tags       = EXCLUDED.condition_tags,
    life_stage_tags      = EXCLUDED.life_stage_tags,
    active               = TRUE,
    popularity_rank      = EXCLUDED.popularity_rank,
    monthly_units_sold   = EXCLUDED.monthly_units_sold,
    price_per_unit_paise = EXCLUDED.price_per_unit_paise,
    in_stock             = EXCLUDED.in_stock,
    dosage               = EXCLUDED.dosage,
    repeat_frequency     = EXCLUDED.repeat_frequency,
    notes                = EXCLUDED.notes;

DO $$
DECLARE c INTEGER;
BEGIN
    SELECT COUNT(*) INTO c FROM product_medicines;
    RAISE NOTICE 'product_medicines rows after upsert: %', c;
END $$;

COMMIT;
