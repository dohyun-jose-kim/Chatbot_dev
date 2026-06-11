"""
PubMed Entrez API를 이용한 수산부산물 기능성 논문 초록 수집 스크립트 (v3)

쿼리 구조: (PART) AND (CATEGORY) AND (FN)
- PART: 수산부산물 부위/형태 키워드 (fish bone, chitin, chitosan 등)
- CATEGORY: 수산 생물 분류 (fish, shrimp, seaweed, mollusk 등)
- FN: 생리활성 기능 키워드 (antioxidant, anti-inflammatory 등)

쿼리 변경 이력 (docs/changes_by_versions.md 참고):
- v1: 초기 쿼리 → ~100,000건 (broad terms로 노이즈 심함)
- v2: NOT human 추가 → 801건 (임상시험 논문까지 제거하는 모순)
- v3 (현재):
  - NOT 조건 제거 → 1,702건 (임상시험 논문 복구)
  - EVIDENCE 블록 제거 → 6,853건 (기능성 키워드 자체가 실험 논문 내포)
  - broad terms 정리 (foot, mantle, residue* 등 제거/한정)
  - 동의어 확장 (chitin, chitosan, seaweed, mussel, scallop 등 추가)

API 방식:
- ESearch(POST) → PMID 목록 수집 (usehistory)
- EFetch(POST) → XML batch 다운로드 후 파싱
- POST 사용 이유: 쿼리 길이가 GET URL 제한을 초과하므로
- CSV 저장 (utf-8-sig)

사용법:
    python collect_pubmed.py count   # 결과 수만 확인
    python collect_pubmed.py test    # 10건 샘플 테스트
    python collect_pubmed.py         # 전체 수집
"""

import os
import sys
import time
import xml.etree.ElementTree as ET

import pandas as pd
import requests

# ── 설정 ──────────────────────────────────────────────────────────
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")
EMAIL = os.environ.get("NCBI_EMAIL", "your_email@example.com")

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

BATCH_SIZE = 500
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds, doubles each retry
SAVE_EVERY = 1000  # 중간 저장 간격 (건수)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "results.csv")
TEMP_CSV = os.path.join(SCRIPT_DIR, "results_temp.csv")

# rate limit: API key 있으면 10 req/sec (0.1초), 없으면 3 req/sec (0.34초)
REQUEST_INTERVAL = 0.1 if NCBI_API_KEY else 0.34

# ── 검색 쿼리 (v3) ────────────────────────────────────────────────
# 구조: (PART) AND (CATEGORY) AND (FN)
# - NOT 조건 없음 (v2에서 임상시험 논문 제거 문제로 삭제)
# - EVIDENCE 블록 없음 (FN 키워드 자체가 실험 논문을 내포)
# 키워드 상세 목록: docs/fetch.md 참고
QUERY = (
    # ── PART: 수산부산물 부위/형태 ──
    '("fish bone*"[tiab] OR "fish scale*"[tiab] OR "fish skin"[tiab] '
    'OR "viscera"[tiab] OR "offal"[tiab] '
    'OR "fish head*"[tiab] OR "fish fin*"[tiab] OR "fish tail*"[tiab] '
    'OR "fish roe"[tiab] OR "fish egg*"[tiab] '
    'OR "shell waste*"[tiab] OR "shrimp shell*"[tiab] OR "crab shell*"[tiab] OR "exoskeleton*"[tiab] '
    'OR "adductor muscle*"[tiab] '
    'OR "processing waste*"[tiab] OR "processing residue*"[tiab] '
    'OR "extract residue*"[tiab] '
    'OR "holdfast*"[tiab] OR "thallus"[tiab] '
    'OR "kelp blade*"[tiab] OR "algal blade*"[tiab] OR "seaweed blade*"[tiab] '
    'OR "kelp stipe*"[tiab] OR "algal stipe*"[tiab] OR "seaweed stipe*"[tiab] '
    'OR "byproduct*"[tiab] OR "by-product*"[tiab] '
    'OR "fish maw"[tiab] OR "swim bladder"[tiab] '
    'OR "fish meal"[tiab] OR "fishmeal"[tiab] OR "fish silage"[tiab] '
    'OR "fish gelatin"[tiab] OR "fish cartilage"[tiab] '
    'OR "fish liver"[tiab] OR "fish gut*"[tiab] OR "fish intestin*"[tiab] '
    'OR "cephalothorax"[tiab] OR "hepatopancreas"[tiab] '
    'OR "shrimp head*"[tiab] OR "fish trimmings"[tiab] OR "fish frame*"[tiab] '
    'OR "chitin"[tiab] OR "chitosan"[tiab]) '
    # ── CATEGORY: 수산 생물 분류 ──
    'AND '
    '("fish"[tiab] OR "fishery"[tiab] OR "Fishes"[MeSH] '
    'OR "crustacean*"[tiab] OR "shrimp"[tiab] OR "crab"[tiab] OR "krill"[tiab] OR "lobster"[tiab] OR "crayfish"[tiab] OR "Crustacea"[MeSH] '
    'OR "mollusk*"[tiab] OR "mollusc*"[tiab] OR "squid"[tiab] OR "abalone"[tiab] OR "oyster"[tiab] '
    'OR "mussel"[tiab] OR "scallop"[tiab] OR "clam"[tiab] OR "octopus"[tiab] OR "cuttlefish"[tiab] OR "Mollusca"[MeSH] '
    'OR "seaweed"[tiab] OR "macroalga*"[tiab] '
    'OR "brown algae"[tiab] OR "Phaeophyceae"[tiab] OR "kelp"[tiab] OR "Sargassum"[tiab] '
    'OR "Undaria"[tiab] OR "Laminaria"[tiab] OR "Fucus"[tiab] OR "Ecklonia"[tiab] OR "Phaeophyceae"[MeSH] '
    'OR "red algae"[tiab] OR "Rhodophyta"[tiab] OR "Gracilaria"[tiab] OR "Porphyra"[tiab] OR "Gelidium"[tiab] OR "Rhodophyta"[MeSH] '
    'OR "green algae"[tiab] OR "Chlorophyta"[tiab] OR "Ulva"[tiab] OR "Chlorophyta"[MeSH] '
    'OR "sea cucumber"[tiab] OR "sea urchin"[tiab] OR "jellyfish"[tiab] OR "starfish"[tiab] '
    'OR "tunicate*"[tiab] OR "sea squirt"[tiab] OR "Echinodermata"[MeSH]) '
    # ── FN: 생리활성 기능 ──
    'AND '
    '("anti-inflammatory"[tiab] OR "immunomodulat*"[tiab] '
    'OR "antithrombotic"[tiab] OR "anticoagulant"[tiab] OR "fibrinolytic"[tiab] '
    'OR "antihypertensive"[tiab] OR "ACE inhibit*"[tiab] OR "angiotensin converting enzyme"[tiab] '
    'OR "hypocholesterolemic"[tiab] OR "cholesterol lower*"[tiab] '
    'OR "blood circulation"[tiab] OR "vasodilat*"[tiab] '
    'OR "hypoglycemic"[tiab] OR "anti-diabetic"[tiab] OR "alpha-glucosidase"[tiab] OR "DPP-IV"[tiab] '
    'OR "lipid metabolism"[tiab] OR "hypolipidemic"[tiab] '
    'OR "anti-obesity"[tiab] '
    'OR "osteoblast*"[tiab] OR "bone health"[tiab] OR "osteoporosis"[tiab] '
    'OR "chondroprotect*"[tiab] OR "cartilage"[tiab] '
    'OR "skin health"[tiab] OR "collagen"[tiab] OR "tyrosinase"[tiab] '
    'OR "antioxidant"[tiab] OR "radical scaveng*"[tiab] OR "DPPH"[tiab] OR "ABTS"[tiab] OR "FRAP"[tiab] '
    'OR "anti-aging"[tiab] OR "anti-ageing"[tiab] OR "elastase"[tiab] '
    'OR "photoprotect*"[tiab] OR "UV protect*"[tiab] '
    'OR "gut health"[tiab] OR "prebiotic"[tiab] '
    'OR "digestibility"[tiab] '
    'OR "hepatoprotect*"[tiab] '
    'OR "detoxif*"[tiab] '
    'OR "neuroprotect*"[tiab] OR "cognitive function"[tiab] OR "cognitive enhancement"[tiab] '
    'OR "memory improv*"[tiab] '
    'OR "eye health"[tiab] OR "retinal protect*"[tiab] '
    'OR "anti-fatigue"[tiab] '
    'OR "calcium absorption"[tiab] '
    'OR "wound healing"[tiab] '
    'OR "antimicrobial"[tiab] OR "antibacterial"[tiab] OR "antifungal"[tiab] OR "antiviral"[tiab] '
    'OR "anticancer"[tiab] OR "antitumor"[tiab] OR "antiproliferative"[tiab] OR "cytotoxic*"[tiab] '
    'OR "cardioprotect*"[tiab] OR "renoprotect*"[tiab])'
)


# ── 유틸리티 ──────────────────────────────────────────────────────
def _request_with_retry(url, params, method="post", max_retries=MAX_RETRIES):
    """HTTP 요청 + 재시도 (exponential backoff). 기본 POST (긴 쿼리 지원)."""
    for attempt in range(max_retries):
        try:
            time.sleep(REQUEST_INTERVAL)
            if method == "post":
                resp = requests.post(url, data=params, timeout=60)
            else:
                resp = requests.get(url, params=params, timeout=60)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            wait = RETRY_BACKOFF * (2 ** attempt)
            print(f"  [retry {attempt+1}/{max_retries}] {e} — {wait}s 대기")
            time.sleep(wait)
    print("ERROR: 최대 재시도 횟수 초과")
    sys.exit(1)


# ── 1단계: ESearch ────────────────────────────────────────────────
def esearch(query, count_only=False):
    """ESearch 실행. count_only=True면 Count만 반환."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": 0,
        "usehistory": "y",
        "email": EMAIL,
    }
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY

    print("ESearch 요청 중...")
    resp = _request_with_retry(ESEARCH_URL, params)
    root = ET.fromstring(resp.text)

    count = int(root.findtext("Count", "0"))
    web_env = root.findtext("WebEnv", "")
    query_key = root.findtext("QueryKey", "")

    print(f"  결과 수: {count:,}")

    if count_only:
        return count

    if not web_env or not query_key:
        print("ERROR: WebEnv/QueryKey를 받지 못했습니다.")
        sys.exit(1)

    return count, web_env, query_key


# ── 2단계: EFetch (batch) ─────────────────────────────────────────
def parse_article(article_elem):
    """PubmedArticle XML 요소에서 필드 추출"""
    medline = article_elem.find("MedlineCitation")
    if medline is None:
        return None

    pmid = medline.findtext("PMID", "")

    art = medline.find("Article")
    if art is None:
        return None

    title = art.findtext("ArticleTitle", "")

    # Abstract — 여러 AbstractText 요소를 합침
    abstract_parts = []
    abs_elem = art.find("Abstract")
    if abs_elem is not None:
        for at in abs_elem.findall("AbstractText"):
            label = at.get("Label", "")
            text = "".join(at.itertext())
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
    abstract = " ".join(abstract_parts)

    # Authors
    authors = []
    author_list = art.find("AuthorList")
    if author_list is not None:
        for au in author_list.findall("Author"):
            last = au.findtext("LastName", "")
            fore = au.findtext("ForeName", "")
            if last:
                authors.append(f"{last} {fore}".strip())
    authors_str = "; ".join(authors)

    # Journal
    journal_elem = art.find("Journal")
    journal = ""
    if journal_elem is not None:
        journal = journal_elem.findtext("Title", "")

    # Year
    pub_date = art.find("Journal/JournalIssue/PubDate")
    year = ""
    if pub_date is not None:
        year = pub_date.findtext("Year", "")
        if not year:
            medline_date = pub_date.findtext("MedlineDate", "")
            if medline_date:
                year = medline_date[:4]

    # MeSH Terms
    mesh_list = medline.find("MeshHeadingList")
    mesh_terms = []
    if mesh_list is not None:
        for mh in mesh_list.findall("MeshHeading"):
            desc = mh.findtext("DescriptorName", "")
            if desc:
                mesh_terms.append(desc)
    mesh_str = "; ".join(mesh_terms)

    return {
        "pmid": pmid,
        "title": title,
        "abstract": abstract,
        "authors": authors_str,
        "journal": journal,
        "year": year,
        "mesh_terms": mesh_str,
    }


def efetch_batch(web_env, query_key, total_count):
    """EFetch로 전체 결과를 batch 단위로 가져옴"""
    all_records = []

    for start in range(0, total_count, BATCH_SIZE):
        params = {
            "db": "pubmed",
            "query_key": query_key,
            "WebEnv": web_env,
            "retstart": start,
            "retmax": BATCH_SIZE,
            "rettype": "xml",
            "retmode": "xml",
            "email": EMAIL,
        }
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY

        fetched_so_far = len(all_records)
        print(f"  EFetch {start+1}–{min(start+BATCH_SIZE, total_count)} / {total_count}  (저장: {fetched_so_far})")

        resp = _request_with_retry(EFETCH_URL, params)

        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError as e:
            print(f"  XML 파싱 에러 (batch start={start}): {e} — 건너뜀")
            continue

        for article in root.findall("PubmedArticle"):
            record = parse_article(article)
            if record:
                all_records.append(record)

        # 중간 저장
        if len(all_records) >= SAVE_EVERY and len(all_records) % SAVE_EVERY < BATCH_SIZE:
            df_temp = pd.DataFrame(all_records)
            df_temp.to_csv(TEMP_CSV, index=False, encoding="utf-8-sig")
            print(f"  → 중간 저장: {TEMP_CSV} ({len(all_records)}건)")

    return all_records


# ── 메인 ──────────────────────────────────────────────────────────
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"

    if mode == "count":
        esearch(QUERY, count_only=True)
        return

    if mode == "test":
        # 소량 테스트: 10건만 fetch
        count, web_env, query_key = esearch(QUERY)
        params = {
            "db": "pubmed",
            "query_key": query_key,
            "WebEnv": web_env,
            "retstart": 0,
            "retmax": 10,
            "rettype": "xml",
            "retmode": "xml",
            "email": EMAIL,
        }
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY

        time.sleep(REQUEST_INTERVAL)
        resp = requests.get(EFETCH_URL, params=params, timeout=30)
        root = ET.fromstring(resp.content)

        for article in root.findall("PubmedArticle"):
            rec = parse_article(article)
            if rec:
                print(f"\n  PMID: {rec['pmid']}")
                print(f"  Title: {rec['title'][:80]}...")
                print(f"  Year: {rec['year']}")
                print(f"  Abstract: {rec['abstract'][:100]}...")
        return

    # full 모드
    print("=" * 60)
    print("PubMed 수산부산물 기능성 논문 수집")
    print("=" * 60)

    if not NCBI_API_KEY:
        print("WARNING: NCBI_API_KEY가 설정되지 않았습니다. Rate limit: 3 req/sec")

    count, web_env, query_key = esearch(QUERY)

    if count == 0:
        print("결과가 없습니다. 쿼리를 확인해주세요.")
        return

    proceed = input(f"\n{count:,}건을 수집합니다. 계속하시겠습니까? (y/n): ")
    if proceed.lower() != "y":
        print("취소되었습니다.")
        return

    print(f"\nEFetch 시작 (batch size: {BATCH_SIZE})...")
    records = efetch_batch(web_env, query_key, count)

    # 최종 저장
    df = pd.DataFrame(records)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n완료! {len(records):,}건 저장 → {OUTPUT_CSV}")

    # 임시 파일 정리
    if os.path.exists(TEMP_CSV):
        os.remove(TEMP_CSV)
        print(f"임시 파일 삭제: {TEMP_CSV}")


if __name__ == "__main__":
    main()
