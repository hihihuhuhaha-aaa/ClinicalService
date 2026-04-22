SELECT id, patient_id, systolic, diastolic, source, day_period,
       position, rested_minutes, device_type, device_validated,
       status, severity, created_at
FROM bp_records
ORDER BY created_at DESC;
