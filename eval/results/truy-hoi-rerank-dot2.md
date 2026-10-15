| Bộ câu hỏi | Cấu hình | R@1 | R@3 | R@10 | MRR | nDCG@3 | ms/câu |
|---|---|---|---|---|---|---|---|
| test_questions_01.json | vector | 80.6% | 100.0% | 100.0% | 0.887 | 0.916 | 702 |
| test_questions_02.json | vector | 90.0% | 90.0% | 90.0% | 0.900 | 0.900 | 2948 |
| dev_questions_dot1.json | vector | 95.0% | 95.0% | 100.0% | 0.963 | 0.950 | 2089 |
| dev_questions_dot2.json | vector | 66.7% | 93.3% | 100.0% | 0.817 | 0.835 | 3617 |
| test_questions_01.json | rerank | 80.6% | 100.0% | 100.0% | 0.892 | 0.920 | 1141 |
| test_questions_02.json | rerank | 60.0% | 90.0% | 90.0% | 0.750 | 0.789 | 1249 |
| dev_questions_dot1.json | rerank | 80.0% | 95.0% | 95.0% | 0.867 | 0.888 | 1188 |
| dev_questions_dot2.json | rerank | 73.3% | 100.0% | 100.0% | 0.856 | 0.893 | 1854 |
| test_questions_01.json | rerank-top10 | 80.6% | 100.0% | 100.0% | 0.892 | 0.920 | 2492 |
| test_questions_02.json | rerank-top10 | 60.0% | 90.0% | 90.0% | 0.750 | 0.789 | 1286 |
| dev_questions_dot1.json | rerank-top10 | 80.0% | 95.0% | 100.0% | 0.879 | 0.888 | 1209 |
| dev_questions_dot2.json | rerank-top10 | 73.3% | 100.0% | 100.0% | 0.856 | 0.893 | 1377 |
| test_questions_01.json | hybrid+rerank | 83.9% | 100.0% | 100.0% | 0.909 | 0.932 | 1237 |
| test_questions_02.json | hybrid+rerank | 60.0% | 90.0% | 90.0% | 0.733 | 0.776 | 1202 |
| dev_questions_dot1.json | hybrid+rerank | 80.0% | 90.0% | 90.0% | 0.850 | 0.863 | 1199 |
| dev_questions_dot2.json | hybrid+rerank | 80.0% | 93.3% | 93.3% | 0.867 | 0.884 | 1242 |
