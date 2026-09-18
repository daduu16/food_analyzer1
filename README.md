# FoodLens AI

FoodLens AI yemək şəklindən ingredientləri və təxmini porsiyaları müəyyən edir, hər ingredientin qida dəyərini tapır və ümumi kalori/makroları hesablayır. Layihə həm tam offline demo, həm də real VLM + USDA rejimi ilə işləyir.

## İmkanlar

- FastAPI `POST /analyze` multipart endpoint-i
- JPEG/PNG magic-byte, ölçü və boş fayl validasiyası
- Anthropic, OpenAI və Gemini VLM dəstəyi (verilmiş `ai/` modulu)
- `asyncio.gather` və semaphore ilə paralel nutrition lookup
- exponential backoff + jitter ilə retry
- normalize olunan 24 saatlıq in-memory TTL cache
- PostgreSQL analiz tarixçəsi; DB verilmədikdə development üçün memory fallback
- Yüklənmiş şəkillərin `uploads/` qovluğunda saxlanması və history ilə image path əlaqəsi
- partial result və unknown-meal üçün strukturlaşdırılmış cavab
- CLI, responsive web UI, Docker Compose və offline testlər

## Lokal quraşdırma

Python 3.10+ tələb olunur.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` daxilində `OFFLINE_MODE=true` saxlayaraq API açarı olmadan işlədin:

```bash
uvicorn foodanalyzer.api:app --reload
```

Sonra `http://localhost:8000` və API sənədləri üçün `http://localhost:8000/docs` açılır.

## Docker ilə

```bash
cp .env.example .env
docker compose up --build
```

Bu üsul API və PostgreSQL-i birlikdə başladır. Data named volume-da qalır.

PyCharm-dan API-ni lokal başladıb yalnız PostgreSQL-i Docker-da işlətmək üçün:

```bash
docker compose up -d db
uvicorn foodanalyzer.api:app --reload
```

Lokal `.env` üçün database host-u `127.0.0.1:5433`, Docker daxilində API üçün isə `db` olur.

## Real AI rejimi

`.env` daxilində `OFFLINE_MODE=false` edin, bir VLM provider və USDA açarı yazın:

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.6-flash
GOOGLE_API_KEY=...
USDA_API_KEY=...
NUTRITION_PROVIDER=usda
```

Seçilən provider SDK-sını ayrıca quraşdırın: `google-genai`, `openai` və ya `anthropic`.

## API nümunələri

```bash
curl -F "image=@data/rice_chicken_broccoli.png" http://localhost:8000/analyze
curl http://localhost:8000/history
curl http://localhost:8000/health
```

`POST /analyze` cavabı `completed`, `partial` və ya `not_recognized` statusu, ingredient sətirləri, hər sətir üzrə nutrition və totals qaytarır.

## CLI

```bash
python -m foodanalyzer analyze data/rice_chicken_broccoli.png --offline
```

## Testlər

Bütün testlər provider şəbəkəsinə çıxmadan işləyir:

```bash
pytest --cov=foodanalyzer --cov-report=term-missing
```

## AI sorğusu, keş, retry və konkurensiya

`AIService` verilən `ai.identify_ingredients` və nutrition provider çağırışlarını bir adapterdə saxlayır.
Hər provider sorğusunda timeout, exponential backoff və kiçik jitter ilə retry tətbiq olunur;
son cəhddən sonra aydın `ProviderError` qaytarılır. Bu, USDA və VLM müvəqqəti əlçatan olmadıqda
partial nəticə göstərməyə imkan verir.

`NutritionCache` ingredient adını normallaşdırır və nəticəni 24 saat (`CACHE_TTL_SECONDS=86400`)
yadda saxlayır. Nutrition lookup-ları `asyncio.gather` ilə paralel işlədir, `Semaphore(10)` isə
eyni anda provider-ə göndərilən sorğuların sayını məhdudlaşdırır. Beləliklə bir ingredientdə yaranan
xəta qalan ingredientlərin nəticəsini ləğv etmir.

## Arxitektura

```text
HTTP / CLI -> Analyzer -> AIService -> ai.identify_ingredients
                         -> TTL Cache -> NutritionProvider (parallel + retry)
             Analyzer -> compute_totals -> Repository -> PostgreSQL
```

`ai/` müəllimin verdiyi müqavilədir və dəyişdirilməyib. Business logic provider SDK-larını birbaşa çağırmır.

## Qeyd

Şəkildən porsiya və nutrition nəticələri təxminidir. Məhsul tibbi diaqnostika və ya peşəkar dietoloq məsləhətinin əvəzi deyil.
