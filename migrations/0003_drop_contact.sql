-- Функция «статус контакта» удалена
ALTER TABLE matches DROP COLUMN IF EXISTS contact_status;
ALTER TABLE matches DROP COLUMN IF EXISTS contact_updated_at;
