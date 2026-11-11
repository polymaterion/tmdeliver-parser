-- Ссылка на профиль автора сообщения (для кнопки «Профиль»)
ALTER TABLE matches ADD COLUMN profile_url TEXT;

-- Кнопка «Дубликат» убрана: оценки только useful / irrelevant
DELETE FROM feedback WHERE verdict = 'duplicate';
ALTER TABLE feedback DROP CONSTRAINT IF EXISTS feedback_verdict_check;
ALTER TABLE feedback ADD CONSTRAINT feedback_verdict_check CHECK (verdict IN ('useful', 'irrelevant'));
