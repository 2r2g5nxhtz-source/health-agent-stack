insert into services (slug, name, category, website_url, priority_tier, market_segment, notes)
values
  ('chatgpt', 'ChatGPT', 'llm', 'https://chatgpt.com', 1, 'assistant', 'Tier 1 core assistant'),
  ('claude', 'Claude', 'llm', 'https://claude.ai', 1, 'assistant', 'Tier 1 core assistant'),
  ('gemini', 'Gemini', 'llm', 'https://gemini.google.com', 1, 'assistant', 'Tier 1 core assistant'),
  ('copilot', 'Microsoft Copilot', 'llm', 'https://copilot.microsoft.com', 1, 'assistant', 'Tier 1 core assistant'),
  ('cursor', 'Cursor', 'developer_tool', 'https://cursor.com', 1, 'coding', 'Tier 1 coding tool'),
  ('midjourney', 'Midjourney', 'image', 'https://www.midjourney.com', 2, 'creative', 'Tier 2 creative tool'),
  ('perplexity', 'Perplexity', 'search', 'https://www.perplexity.ai', 2, 'research', 'Tier 2 research tool'),
  ('elevenlabs', 'ElevenLabs', 'audio', 'https://elevenlabs.io', 2, 'voice', 'Tier 2 voice tool'),
  ('runway', 'Runway', 'video', 'https://runwayml.com', 2, 'creative', 'Tier 2 video tool'),
  ('heygen', 'HeyGen', 'video', 'https://www.heygen.com', 2, 'avatar_video', 'Tier 2 avatar tool'),
  ('mistral', 'Mistral', 'llm', 'https://mistral.ai', 3, 'model_platform', 'Tier 3 model platform'),
  ('grok', 'Grok', 'llm', 'https://grok.com', 3, 'assistant', 'Tier 3 assistant'),
  ('replit', 'Replit', 'developer_tool', 'https://replit.com', 3, 'coding', 'Tier 3 developer platform'),
  ('suno', 'Suno', 'audio', 'https://suno.com', 3, 'music', 'Tier 3 music generation'),
  ('pika', 'Pika', 'video', 'https://pika.art', 3, 'video', 'Tier 3 video generation'),
  ('invideo', 'InVideo', 'video', 'https://invideo.io', 3, 'video', 'Tier 3 video editor')
on conflict (slug) do update set
  name = excluded.name,
  category = excluded.category,
  website_url = excluded.website_url,
  priority_tier = excluded.priority_tier,
  market_segment = excluded.market_segment,
  notes = excluded.notes,
  is_active = true;

insert into sources (service_id, source_type, source_url, parser_type, priority, fetch_frequency, is_active)
select s.id, v.source_type::source_type_enum, v.source_url, v.parser_type, v.priority, v.fetch_frequency, true
from services s
join (
  values
    ('chatgpt', 'pricing', 'https://chatgpt.com/pricing', 'html_pricing', 10, 'daily'),
    ('chatgpt', 'official', 'https://openai.com/news/', 'html_changelog', 15, 'daily'),
    ('claude', 'pricing', 'https://www.anthropic.com/pricing', 'html_pricing', 10, 'daily'),
    ('claude', 'official', 'https://www.anthropic.com/news', 'html_changelog', 15, 'daily'),
    ('gemini', 'pricing', 'https://one.google.com/about/google-ai-plans/', 'html_pricing', 10, 'daily'),
    ('gemini', 'official', 'https://blog.google/products/gemini/', 'html_changelog', 15, 'daily'),
    ('copilot', 'pricing', 'https://www.microsoft.com/en-us/store/b/copilotpro', 'html_pricing', 10, 'daily'),
    ('copilot', 'official', 'https://blogs.microsoft.com/blog/tag/copilot/', 'html_changelog', 15, 'daily'),
    ('cursor', 'pricing', 'https://cursor.com/pricing', 'html_pricing', 10, 'daily'),
    ('cursor', 'official', 'https://cursor.com/changelog', 'html_changelog', 15, 'daily'),
    ('midjourney', 'official', 'https://docs.midjourney.com/changelog', 'html_changelog', 20, 'every_2_days'),
    ('perplexity', 'pricing', 'https://www.perplexity.ai/pro', 'html_pricing', 20, 'every_2_days'),
    ('perplexity', 'official', 'https://www.perplexity.ai/hub/blog', 'html_changelog', 25, 'every_2_days'),
    ('elevenlabs', 'pricing', 'https://elevenlabs.io/pricing', 'html_pricing', 20, 'every_2_days'),
    ('elevenlabs', 'official', 'https://elevenlabs.io/blog', 'html_changelog', 25, 'every_2_days'),
    ('runway', 'pricing', 'https://runwayml.com/pricing/', 'html_pricing', 20, 'every_2_days'),
    ('runway', 'official', 'https://runwayml.com/research/', 'html_changelog', 25, 'every_2_days'),
    ('heygen', 'pricing', 'https://www.heygen.com/pricing', 'html_pricing', 20, 'every_2_days'),
    ('heygen', 'official', 'https://www.heygen.com/blog', 'html_changelog', 25, 'every_2_days'),
    ('mistral', 'official', 'https://mistral.ai/news/', 'html_changelog', 30, 'twice_weekly'),
    ('grok', 'official', 'https://x.ai/news', 'html_changelog', 30, 'twice_weekly'),
    ('replit', 'pricing', 'https://replit.com/pricing', 'html_pricing', 30, 'twice_weekly'),
    ('replit', 'official', 'https://blog.replit.com', 'html_changelog', 35, 'twice_weekly'),
    ('suno', 'pricing', 'https://suno.com/pricing', 'html_pricing', 30, 'twice_weekly'),
    ('suno', 'official', 'https://suno.com/blog', 'html_changelog', 35, 'twice_weekly'),
    ('pika', 'pricing', 'https://pika.art/pricing', 'html_pricing', 30, 'twice_weekly'),
    ('pika', 'official', 'https://pika.art/blog', 'html_changelog', 35, 'twice_weekly'),
    ('invideo', 'pricing', 'https://invideo.io/pricing/', 'html_pricing', 30, 'twice_weekly'),
    ('invideo', 'official', 'https://invideo.io/blog/', 'html_changelog', 35, 'twice_weekly')
) as v(service_slug, source_type, source_url, parser_type, priority, fetch_frequency)
  on s.slug = v.service_slug
on conflict (source_url) do update set
  service_id = excluded.service_id,
  source_type = excluded.source_type,
  parser_type = excluded.parser_type,
  priority = excluded.priority,
  fetch_frequency = excluded.fetch_frequency,
  is_active = true;

insert into sources (service_id, source_type, source_url, parser_type, priority, fetch_frequency, is_active)
values
  (null, 'launch', 'https://www.producthunt.com/topics/artificial-intelligence', 'html_listing', 40, 'daily', true),
  (null, 'marketplace', 'https://appsumo.com/search/?q=AI', 'html_marketplace', 45, 'daily', true)
on conflict (source_url) do update set
  source_type = excluded.source_type,
  parser_type = excluded.parser_type,
  priority = excluded.priority,
  fetch_frequency = excluded.fetch_frequency,
  is_active = true;
