-- Get all Singapore documents
SELECT title, products, link_guidance, updated_at 
FROM source.medical_guidelines 
WHERE country = 'Singapore'
ORDER BY updated_at DESC;

-- Search by product type (Medical Device or Drugs)
SELECT title, products, link_guidance
FROM source.medical_guidelines 
WHERE country = 'Singapore' 
  AND products = 'Medical Device';  -- or 'Drugs' for therapeutic products

-- Full text search in document content
SELECT title, products, link_guidance
FROM source.medical_guidelines 
WHERE country = 'Singapore' 
  AND (all_text ILIKE '%safety%' OR title ILIKE '%safety%');

-- Search by document section/category (using json_data)
SELECT title, products, json_data->>'section' as section
FROM source.medical_guidelines 
WHERE country = 'Singapore' 
  AND json_data->>'section' ILIKE '%Clinical%';

-- Get recently updated documents
SELECT title, products, updated_at
FROM source.medical_guidelines 
WHERE country = 'Singapore' 
  AND updated_at >= NOW() - INTERVAL '7 days'
ORDER BY updated_at DESC;

-- Complex search combining multiple criteria
SELECT title, products, json_data->>'section' as section
FROM source.medical_guidelines 
WHERE country = 'Singapore' 
  AND products = 'Medical Device'
  AND (
    all_text ILIKE '%safety%' 
    OR title ILIKE '%safety%'
    OR json_data->>'section' ILIKE '%safety%'
  );

-- Count documents by section
SELECT json_data->>'section' as section, COUNT(*) as count
FROM source.medical_guidelines 
WHERE country = 'Singapore'
GROUP BY json_data->>'section'
ORDER BY count DESC;

-- Find documents with specific keywords (using full text search)
SELECT title, products, 
       ts_headline(all_text, to_tsquery('english', 'clinical & trial')) as matched_text
FROM source.medical_guidelines 
WHERE country = 'Singapore' 
  AND to_tsvector('english', all_text) @@ to_tsquery('english', 'clinical & trial');
