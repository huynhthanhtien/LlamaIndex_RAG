from pathlib import Path


def parse_md(path: Path) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    chunks = content.split("Câu hỏi:")
    results: list[dict[str, str]] = []
    for c in chunks[1:]:
        lines = [l.strip() for l in c.strip().split("\n") if l.strip()]
        if not lines:
            continue
        q = lines[0]
        nguon = ""
        ans_lines: list[str] = []
        for l in lines[1:]:
            if l.startswith("Nguồn:"):
                nguon = l[6:].strip()
            else:
                ans_lines.append(l)
        ans = "\n".join(ans_lines).strip()
        results.append({"q": q, "ans": ans, "nguon": nguon})
    return results


def is_not_found(ans: str) -> bool:
    ans_lower = ans.lower()
    return "không tìm thấy" in ans_lower or ans == "" or "/no_think" in ans


def main():
    root = Path(__file__).resolve().parent.parent
    r_old = parse_md(root / "eval" / "results" / "test-basic.md")
    r_new = parse_md(root / "eval" / "results" / "cau-hoi01-result.md")

    print(f"Tổng số câu: Cũ = {len(r_old)} | Mới = {len(r_new)}")

    not_found_old = sum(1 for r in r_old if is_not_found(r["ans"]))
    not_found_new = sum(1 for r in r_new if is_not_found(r["ans"]))

    print(f"Bản cũ (test-basic.md): Trả lời = {len(r_old) - not_found_old} ({(len(r_old) - not_found_old)/len(r_old):.1%}), Từ chối/Không tìm thấy = {not_found_old} ({not_found_old/len(r_old):.1%})")
    print(f"Bản mới (cau-hoi01-result.md): Trả lời = {len(r_new) - not_found_new} ({(len(r_new) - not_found_new)/len(r_new):.1%}), Từ chối/Không tìm thấy = {not_found_new} ({not_found_new/len(r_new):.1%})")

    print("\n" + "="*80)
    print("1. CÁC CÂU BẢN CŨ NÓI 'KHÔNG TÌM THẤY' NHƯNG BẢN MỚI ĐÃ TRẢ LỜI ĐƯỢC:")
    print("="*80)
    for i in range(min(len(r_old), len(r_new))):
        old_nf = is_not_found(r_old[i]["ans"])
        new_nf = is_not_found(r_new[i]["ans"])
        q = r_new[i]["q"]
        if old_nf and not new_nf:
            print(f"\n[+] Câu {i+1}: {q}")
            print(f"    - Cũ: {r_old[i]['ans']}")
            print(f"    - Mới: {r_new[i]['ans'][:250]}...")
            print(f"    - Nguồn mới: {r_new[i]['nguon'][:120]}...")

    print("\n" + "="*80)
    print("2. CÁC CÂU BẢN CŨ ĐÃ TRẢ LỜI NHƯNG BẢN MỚI TỪ CHỐI / KHÔNG TÌM THẤY:")
    print("="*80)
    for i in range(min(len(r_old), len(r_new))):
        old_nf = is_not_found(r_old[i]["ans"])
        new_nf = is_not_found(r_new[i]["ans"])
        q = r_new[i]["q"]
        if not old_nf and new_nf:
            print(f"\n[-] Câu {i+1}: {q}")
            print(f"    - Cũ: {r_old[i]['ans'][:250]}...")
            print(f"    - Mới: {r_new[i]['ans']}")

    print("\n" + "="*80)
    print("3. SO SÁNH NỘI DUNG VÀ ĐỘ CHÍNH XÁC Ở CÁC CÂU CẢ HAI ĐỀU TRẢ LỜI:")
    print("="*80)
    for i in range(min(len(r_old), len(r_new))):
        old_nf = is_not_found(r_old[i]["ans"])
        new_nf = is_not_found(r_new[i]["ans"])
        q = r_new[i]["q"]
        if not old_nf and not new_nf:
            print(f"\n[*] Câu {i+1}: {q}")
            print(f"    - Cũ: {r_old[i]['ans'][:150]}...")
            print(f"    - Mới: {r_new[i]['ans'][:150]}...")


if __name__ == "__main__":
    main()
