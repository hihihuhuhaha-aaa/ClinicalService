-- ============================================================
-- SEED DATA — clinic_engine
-- Thứ tự insert tuân theo dependency: patients → input → output
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- patients (10 rows)
-- ------------------------------------------------------------
INSERT INTO patients (id, gender, birth_year) VALUES
    ('00000000-0000-0000-0000-000000000001', 'male',   1965),
    ('00000000-0000-0000-0000-000000000002', 'female', 1972),
    ('00000000-0000-0000-0000-000000000003', 'male',   1980),
    ('00000000-0000-0000-0000-000000000004', 'female', 1958),
    ('00000000-0000-0000-0000-000000000005', 'male',   1990),
    ('00000000-0000-0000-0000-000000000006', 'female', 1968),
    ('00000000-0000-0000-0000-000000000007', 'male',   1975),
    ('00000000-0000-0000-0000-000000000008', 'female', 1983),
    ('00000000-0000-0000-0000-000000000009', 'male',   1950),
    ('00000000-0000-0000-0000-000000000010', 'female', 1995);

-- ------------------------------------------------------------
-- bp_records (10 rows — 1 per patient, mixed sources)
-- ------------------------------------------------------------
INSERT INTO bp_records (id, patient_id, systolic, diastolic, source, day_period, position, rested_minutes, device_type, device_validated, status, severity) VALUES
    ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 138, 88, 'HBPM',   'morning', 'sitting', 5,    'upper_arm', true,  'measured', 'mild'),
    ('10000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002', 118, 74, 'HBPM',   'evening', 'sitting', 5,    'upper_arm', true,  'measured', 'normal'),
    ('10000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000003', 155, 95, 'clinic', 'morning', 'sitting', 10,   'upper_arm', true,  'measured', 'moderate'),
    ('10000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000004', 162, 100,'clinic', 'morning', 'sitting', 10,   'upper_arm', true,  'measured', 'severe'),
    ('10000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000005', 122, 78, 'HBPM',   'morning', 'sitting', 5,    'wrist',     false, 'measured', 'normal'),
    ('10000000-0000-0000-0000-000000000006', '00000000-0000-0000-0000-000000000006', 148, 92, 'ABPM',   'day',     'sitting', null, 'upper_arm', true,  'measured', 'mild'),
    ('10000000-0000-0000-0000-000000000007', '00000000-0000-0000-0000-000000000007', 135, 85, 'HBPM',   'evening', 'sitting', 5,    'upper_arm', true,  'measured', 'mild'),
    ('10000000-0000-0000-0000-000000000008', '00000000-0000-0000-0000-000000000008', 112, 70, 'HBPM',   'morning', 'sitting', 5,    'upper_arm', true,  'measured', 'normal'),
    ('10000000-0000-0000-0000-000000000009', '00000000-0000-0000-0000-000000000009', 170, 105,'clinic', 'morning', 'sitting', 10,   'upper_arm', true,  'measured', 'severe'),
    ('10000000-0000-0000-0000-000000000010', '00000000-0000-0000-0000-000000000010', 125, 80, 'ABPM',   'night',   'lying',   null, 'upper_arm', true,  'measured', 'normal');

-- ------------------------------------------------------------
-- clinical_facts (10 rows — Stage 2 risk factors)
-- ------------------------------------------------------------
INSERT INTO clinical_facts (id, patient_id, fact_group, fact_key, value, status, severity, source) VALUES
    ('20000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'cardiovascularRiskFactors', 'diabetes',                   true,  'confirmed', 'moderate', 'ehr'),
    ('20000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002', 'cardiovascularRiskFactors', 'smoking',                    false, 'confirmed', null,       'self_report'),
    ('20000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000003', 'targetOrganDamage',         'lvh',                        true,  'confirmed', 'mild',     'echo'),
    ('20000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000004', 'cardiovascularRiskFactors', 'familial_hypercholesterol',  true,  'confirmed', 'moderate', 'lab'),
    ('20000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000005', 'cardiovascularRiskFactors', 'obesity',                    true,  'confirmed', 'mild',     'clinical'),
    ('20000000-0000-0000-0000-000000000006', '00000000-0000-0000-0000-000000000006', 'comorbidities',             'ckd_stage3',                 true,  'confirmed', 'moderate', 'lab'),
    ('20000000-0000-0000-0000-000000000007', '00000000-0000-0000-0000-000000000007', 'cardiovascularRiskFactors', 'dyslipidemia',               true,  'confirmed', 'mild',     'lab'),
    ('20000000-0000-0000-0000-000000000008', '00000000-0000-0000-0000-000000000008', 'cardiovascularRiskFactors', 'smoking',                    true,  'confirmed', 'moderate', 'self_report'),
    ('20000000-0000-0000-0000-000000000009', '00000000-0000-0000-0000-000000000009', 'comorbidities',             'cvd_established',            true,  'confirmed', 'severe',   'ehr'),
    ('20000000-0000-0000-0000-000000000010', '00000000-0000-0000-0000-000000000010', 'targetOrganDamage',         'microalbuminuria',           true,  'confirmed', 'mild',     'lab');

-- ------------------------------------------------------------
-- clinical_classifications (10 rows — Stage 1 output)
-- ------------------------------------------------------------
INSERT INTO clinical_classifications (id, patient_id, bp_run_id, bp_category, bp_stage, phenotype, source_used, source_value, confidence, flags, rule_version) VALUES
    ('30000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'hypertension', 'stage1',  'sustained',     'home',   '138.0 / 88.0',  'medium', '["borderline"]',          'v1.0'),
    ('30000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000002', 'elevated',     'none',    'unknown',       'home',   '118.0 / 74.0',  'low',    '["borderline","missing_clinic"]', 'v1.0'),
    ('30000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000003', 'hypertension', 'stage2',  'sustained',     'clinic', '155.0 / 95.0',  'high',   '[]',                      'v1.0'),
    ('30000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000004', 'hypertension', 'stage2',  'sustained',     'clinic', '162.0 / 100.0', 'high',   '[]',                      'v1.0'),
    ('30000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000005', '10000000-0000-0000-0000-000000000005', 'elevated',     'none',    'unknown',       'home',   '122.0 / 78.0',  'low',    '["quality_low"]',         'v1.0'),
    ('30000000-0000-0000-0000-000000000006', '00000000-0000-0000-0000-000000000006', '10000000-0000-0000-0000-000000000006', 'hypertension', 'stage1',  'sustained',     'abpm',   '148.0 / 92.0',  'high',   '[]',                      'v1.0'),
    ('30000000-0000-0000-0000-000000000007', '00000000-0000-0000-0000-000000000007', '10000000-0000-0000-0000-000000000007', 'hypertension', 'stage1',  'white_coat',    'home',   '135.0 / 85.0',  'medium', '["borderline"]',          'v1.0'),
    ('30000000-0000-0000-0000-000000000008', '00000000-0000-0000-0000-000000000008', '10000000-0000-0000-0000-000000000008', 'normal',       'none',    'unknown',       'home',   '112.0 / 70.0',  'medium', '[]',                      'v1.0'),
    ('30000000-0000-0000-0000-000000000009', '00000000-0000-0000-0000-000000000009', '10000000-0000-0000-0000-000000000009', 'hypertension', 'stage2',  'sustained',     'clinic', '170.0 / 105.0', 'high',   '[]',                      'v1.0'),
    ('30000000-0000-0000-0000-000000000010', '00000000-0000-0000-0000-000000000010', '10000000-0000-0000-0000-000000000010', 'elevated',     'none',    'masked',        'abpm',   '125.0 / 80.0',  'medium', '["missing_clinic"]',      'v1.0');

-- ------------------------------------------------------------
-- classification_usability (10 rows)
-- ------------------------------------------------------------
INSERT INTO classification_usability (id, classification_id, patient_id, clinic_usable, home_usable, abpm_usable, bp_category_usable, bp_stage_usable, phenotype_usable) VALUES
    ('40000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', false, true,  false, true,  true,  false),
    ('40000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002', false, true,  false, true,  false, false),
    ('40000000-0000-0000-0000-000000000003', '30000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000003', true,  false, false, true,  true,  true),
    ('40000000-0000-0000-0000-000000000004', '30000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000004', true,  false, false, true,  true,  true),
    ('40000000-0000-0000-0000-000000000005', '30000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000005', false, true,  false, true,  false, false),
    ('40000000-0000-0000-0000-000000000006', '30000000-0000-0000-0000-000000000006', '00000000-0000-0000-0000-000000000006', false, false, true,  true,  true,  true),
    ('40000000-0000-0000-0000-000000000007', '30000000-0000-0000-0000-000000000007', '00000000-0000-0000-0000-000000000007', false, true,  false, true,  true,  true),
    ('40000000-0000-0000-0000-000000000008', '30000000-0000-0000-0000-000000000008', '00000000-0000-0000-0000-000000000008', false, true,  false, true,  false, false),
    ('40000000-0000-0000-0000-000000000009', '30000000-0000-0000-0000-000000000009', '00000000-0000-0000-0000-000000000009', true,  false, false, true,  true,  true),
    ('40000000-0000-0000-0000-000000000010', '30000000-0000-0000-0000-000000000010', '00000000-0000-0000-0000-000000000010', false, false, true,  true,  false, true);

-- ------------------------------------------------------------
-- measurement_evaluation (10 rows — 1 per classification, source khớp)
-- ------------------------------------------------------------
INSERT INTO measurement_evaluation (id, patient_id, classification_id, source, quality_score, quality_level, usable, flags, details) VALUES
    ('50000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', 'home',   0.72, 'medium', true,  '["temporal_coverage_low"]',           '{"num_days":3,"pairs_per_session":1.5}'),
    ('50000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000002', 'home',   0.61, 'medium', true,  '["temporal_coverage_low","repeated_measurement_per_session_medium"]', '{"num_days":1,"pairs_per_session":1.0}'),
    ('50000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000003', '30000000-0000-0000-0000-000000000003', 'clinic', 0.90, 'high',   true,  '[]',                                  '{"clinic_readings_count":3,"clinic_rest_minutes":10}'),
    ('50000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000004', '30000000-0000-0000-0000-000000000004', 'clinic', 0.88, 'high',   true,  '[]',                                  '{"clinic_readings_count":3,"clinic_rest_minutes":10}'),
    ('50000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000005', '30000000-0000-0000-0000-000000000005', 'home',   0.45, 'low',    false, '["quality_low","device_not_validated"]','{"num_days":1,"device_validated":false}'),
    ('50000000-0000-0000-0000-000000000006', '00000000-0000-0000-0000-000000000006', '30000000-0000-0000-0000-000000000006', 'abpm',   0.85, 'high',   true,  '[]',                                  '{"duration_hours":24,"valid_reading_ratio":0.92}'),
    ('50000000-0000-0000-0000-000000000007', '00000000-0000-0000-0000-000000000007', '30000000-0000-0000-0000-000000000007', 'home',   0.70, 'medium', true,  '["borderline"]',                      '{"num_days":5,"pairs_per_session":2.0}'),
    ('50000000-0000-0000-0000-000000000008', '00000000-0000-0000-0000-000000000008', '30000000-0000-0000-0000-000000000008', 'home',   0.80, 'high',   true,  '[]',                                  '{"num_days":7,"pairs_per_session":2.0}'),
    ('50000000-0000-0000-0000-000000000009', '00000000-0000-0000-0000-000000000009', '30000000-0000-0000-0000-000000000009', 'clinic', 0.91, 'high',   true,  '[]',                                  '{"clinic_readings_count":3,"clinic_rest_minutes":10}'),
    ('50000000-0000-0000-0000-000000000010', '00000000-0000-0000-0000-000000000010', '30000000-0000-0000-0000-000000000010', 'abpm',   0.78, 'medium', true,  '["missing_clinic"]',                  '{"duration_hours":24,"valid_reading_ratio":0.80}');

-- ------------------------------------------------------------
-- clinical_reasonings (10 rows)
-- ------------------------------------------------------------
INSERT INTO clinical_reasonings (id, classification_id, patient_id, explanation, recommendation, confidence) VALUES
    ('60000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'Gia tri do gan nguong phan loai nen can theo doi sat hon.',                                  'Nen tai kham som, ket hop thay doi loi song va can nhac dieu tri theo danh gia bac si.', 'medium'),
    ('60000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002', 'Thieu du lieu clinic nen khong the ket luan day du.',                                        'Uu tien thay doi loi song va theo doi dinh ky.',                                         'low'),
    ('60000000-0000-0000-0000-000000000003', '30000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000003', 'Du lieu clinic chat luong cao, xac nhan tang huyet ap stage 2.',                            'Can kham chuyen khoa som de danh gia va dieu tri tang huyet ap stage2.',                  'high'),
    ('60000000-0000-0000-0000-000000000004', '30000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000004', 'Huyet ap rat cao, nguy co bien chung cao.',                                                  'Can kham chuyen khoa som de danh gia va dieu tri tang huyet ap stage2.',                  'high'),
    ('60000000-0000-0000-0000-000000000005', '30000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000005', 'Chat luong du lieu thap, do tin cay ket luan bi giam.',                                      'Du lieu chua du tin cay, can do lai dung quy trinh de xac nhan.',                        'low'),
    ('60000000-0000-0000-0000-000000000006', '30000000-0000-0000-0000-000000000006', '00000000-0000-0000-0000-000000000006', 'Du lieu ABPM 24h chat luong tot, xac nhan tang huyet ap stage 1.',                          'Nen tai kham som, ket hop thay doi loi song va can nhac dieu tri theo danh gia bac si.', 'high'),
    ('60000000-0000-0000-0000-000000000007', '30000000-0000-0000-0000-000000000007', '00000000-0000-0000-0000-000000000007', 'Nghi ngo tang huyet ap ao trang (white coat), can theo doi them.',                         'Nen theo doi huyet ap sat hon trong 1-2 tuan va trao doi voi bac si.',                    'medium'),
    ('60000000-0000-0000-0000-000000000008', '30000000-0000-0000-0000-000000000008', '00000000-0000-0000-0000-000000000008', 'Ket qua duoc tong hop tu nguon do co chat luong tot nhat hien co.',                         'Tiep tuc theo doi huyet ap dinh ky va duy tri loi song lanh manh.',                      'medium'),
    ('60000000-0000-0000-0000-000000000009', '30000000-0000-0000-0000-000000000009', '00000000-0000-0000-0000-000000000009', 'Huyet ap rat cao, ket hop tien su benh tim mach, nguy co bien chung nghiem trong.',       'Can kham chuyen khoa som de danh gia va dieu tri tang huyet ap stage2.',                  'high'),
    ('60000000-0000-0000-0000-000000000010', '30000000-0000-0000-0000-000000000010', '00000000-0000-0000-0000-000000000010', 'ABPM ghi nhan tang huyet ap an (masked hypertension), thieu du lieu clinic de xac nhan.', 'Nen theo doi huyet ap sat hon trong 1-2 tuan va trao doi voi bac si.',                    'medium');

-- ------------------------------------------------------------
-- risk_assessments (10 rows — Stage 2 output)
-- ------------------------------------------------------------
INSERT INTO risk_assessments (id, classification_id, patient_id, risk_level, rule_version) VALUES
    ('70000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'high',   'v1.0'),
    ('70000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002', 'low',    'v1.0'),
    ('70000000-0000-0000-0000-000000000003', '30000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000003', 'high',   'v1.0'),
    ('70000000-0000-0000-0000-000000000004', '30000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000004', 'high',   'v1.0'),
    ('70000000-0000-0000-0000-000000000005', '30000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000005', 'low',    'v1.0'),
    ('70000000-0000-0000-0000-000000000006', '30000000-0000-0000-0000-000000000006', '00000000-0000-0000-0000-000000000006', 'high',   'v1.0'),
    ('70000000-0000-0000-0000-000000000007', '30000000-0000-0000-0000-000000000007', '00000000-0000-0000-0000-000000000007', 'medium', 'v1.0'),
    ('70000000-0000-0000-0000-000000000008', '30000000-0000-0000-0000-000000000008', '00000000-0000-0000-0000-000000000008', 'low',    'v1.0'),
    ('70000000-0000-0000-0000-000000000009', '30000000-0000-0000-0000-000000000009', '00000000-0000-0000-0000-000000000009', 'high',   'v1.0'),
    ('70000000-0000-0000-0000-000000000010', '30000000-0000-0000-0000-000000000010', '00000000-0000-0000-0000-000000000010', 'medium', 'v1.0');

-- ------------------------------------------------------------
-- risk_reasonings (10 rows)
-- ------------------------------------------------------------
INSERT INTO risk_reasonings (id, risk_assessment_id, patient_id, explanation, recommendation, confidence, rule_version) VALUES
    ('80000000-0000-0000-0000-000000000001', '70000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'Rule 2 applied: diabetes detected with BP stage1; risk elevated to high.',                                     'Ket hop dieu tri thuoc ha huyet ap va kiem soat duong huyet chat che.',                            'high',   'v1.0'),
    ('80000000-0000-0000-0000-000000000002', '70000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002', 'Rule 1 applied: no significant risk factors; BP elevated only.',                                              'Nguy co thap: uu tien TDLS va theo doi dinh ky; chua can dieu tri thuoc ngay.',                    'low',    'v1.0'),
    ('80000000-0000-0000-0000-000000000003', '70000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000003', 'Rule 2 applied: LVH (target organ damage) with BP stage2; high risk confirmed.',                              'Can kham chuyen khoa tim mach, bat dau dieu tri thuoc theo chi dinh.',                             'high',   'v1.0'),
    ('80000000-0000-0000-0000-000000000004', '70000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000004', 'Rule 2 applied: familial hypercholesterolemia with BP stage2; high risk confirmed.',                          'Can dieu tri phoi hop ha huyet ap va statin lieu cao.',                                            'high',   'v1.0'),
    ('80000000-0000-0000-0000-000000000005', '70000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000005', 'Rule 1 applied: obesity as single risk factor; BP elevated; low risk.',                                       'Giam can va tang cuong van dong the chat la uu tien hang dau.',                                    'low',    'v1.0'),
    ('80000000-0000-0000-0000-000000000006', '70000000-0000-0000-0000-000000000006', '00000000-0000-0000-0000-000000000006', 'Rule 2 applied: CKD stage3 with BP stage1; risk elevated to high per guideline.',                             'Can kiem soat huyet ap muc tieu <130/80 mmHg, bao ve than.',                                       'high',   'v1.0'),
    ('80000000-0000-0000-0000-000000000007', '70000000-0000-0000-0000-000000000007', '00000000-0000-0000-0000-000000000007', 'Rule 1 applied: dyslipidemia as single risk factor; BP stage1; medium risk.',                                 'Ket hop dieu tri thuoc ha huyet ap nhe va statin neu LDL khong dat muc tieu.',                     'medium', 'v1.0'),
    ('80000000-0000-0000-0000-000000000008', '70000000-0000-0000-0000-000000000008', '00000000-0000-0000-0000-000000000008', 'Rule 1 applied: smoking as risk factor; BP normal; low overall risk.',                                        'Tu bo hut thuoc la bien phap hieu qua nhat de giam nguy co tim mach.',                             'low',    'v1.0'),
    ('80000000-0000-0000-0000-000000000009', '70000000-0000-0000-0000-000000000009', '00000000-0000-0000-0000-000000000009', 'Rule 3 applied: established CVD with BP stage2; very high risk.',                                             'Can nhap vien hoac kham khan cap de dieu tri tang huyet ap stage2 tren nen benh CVD.',             'high',   'v1.0'),
    ('80000000-0000-0000-0000-000000000010', '70000000-0000-0000-0000-000000000010', '00000000-0000-0000-0000-000000000010', 'Rule 2 applied: microalbuminuria (target organ damage) with masked hypertension; medium-high risk.',          'Can dieu tri thuoc ha huyet ap va kiem soat ABPM dinh ky de danh gia dap ung dieu tri.',           'medium', 'v1.0');

COMMIT;
