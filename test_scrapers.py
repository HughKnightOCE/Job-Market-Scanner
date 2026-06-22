from src.scraper import fetch_seek_jobs, fetch_jora_jobs, fetch_indeed_jobs, fetch_ethicaljobs_jobs

print("--- Testing Seek ---")
seek = fetch_seek_jobs(["python", "developer"], location="Melbourne", max_pages=1)
print(f"Seek: {len(seek)} jobs")
if seek:
    j = seek[0]
    print(f"  Sample: [{j['source']}] {j['title']} @ {j['company']} | {j['location']} | AUD {j['salary_min']}-{j['salary_max']}")

print("--- Testing Jora ---")
jora = fetch_jora_jobs(["developer"], location="Melbourne", max_pages=1)
print(f"Jora: {len(jora)} jobs")
if jora:
    j = jora[0]
    print(f"  Sample: [{j['source']}] {j['title']} @ {j['company']} | {j['location']}")

print("--- Testing Indeed ---")
indeed = fetch_indeed_jobs(["developer"], location="Melbourne")
print(f"Indeed: {len(indeed)} jobs")
if indeed:
    j = indeed[0]
    print(f"  Sample: [{j['source']}] {j['title']} @ {j['company']}")

print("--- Testing EthicalJobs ---")
ethical = fetch_ethicaljobs_jobs(["developer"], location="Melbourne", max_pages=1)
print(f"EthicalJobs: {len(ethical)} jobs")
if ethical:
    j = ethical[0]
    print(f"  Sample: [{j['source']}] {j['title']} @ {j['company']} | {j['location']} | AUD {j['salary_min']}-{j['salary_max']}")

print("--- All scraper tests done ---")
