-- World-Class Settlement Status Migration
-- Manual SQL for renaming and updating values

BEGIN;

-- Update bills table (if exists)
DO $$
BEGIN
    -- Rename column
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='bills' AND column_name='payment_status') THEN
        ALTER TABLE bills RENAME COLUMN payment_status TO settlement_status;
        
        -- Update values
        UPDATE bills SET settlement_status = 'unsettled' WHERE settlement_status = 'unpaid';
        UPDATE bills SET settlement_status = 'partial_settled' WHERE settlement_status = 'partial';
        UPDATE bills SET settlement_status = 'settled' WHERE settlement_status = 'paid';
        
        RAISE NOTICE 'Bills table updated successfully';
    END IF;
END $$;

-- Update commission_records table (if exists)
DO $$
BEGIN
    -- Rename column
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='commission_records' AND column_name='payment_status') THEN
        ALTER TABLE commission_records RENAME COLUMN payment_status TO settlement_status;
        
        -- Update values (only 2 states for commissions)
        UPDATE commission_records SET settlement_status = 'unsettled' WHERE settlement_status = 'pending';
        UPDATE commission_records SET settlement_status = 'settled' WHERE settlement_status = 'paid';
        
        RAISE NOTICE 'Commission records table updated successfully';
    END IF;
END $$;

-- Update sales table (if exists)
DO $$
BEGIN
    -- Rename column
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sales' AND column_name='payment_status') THEN
        ALTER TABLE sales RENAME COLUMN payment_status TO settlement_status;
        
        -- Update values
        UPDATE sales SET settlement_status = 'unsettled' WHERE settlement_status = 'unpaid';
        UPDATE sales SET settlement_status = 'partial_settled' WHERE settlement_status = 'partial';
        UPDATE sales SET settlement_status = 'settled' WHERE settlement_status = 'paid';
        
        RAISE NOTICE 'Sales table updated successfully';
    END IF;
END $$;

COMMIT;

SELECT 'Settlement status migration completed successfully!' AS status;
