| Cấu hình | R@1 01 | R@1 02 | R@1 đ1 | R@1 đ2 | R@1 đ3 | **R@1 gộp (91 câu)** | R@3 gộp | MRR gộp | ms/câu (trung vị) |
|---|---|---|---|---|---|---|---|---|---|
| vector | 25/31 | 9/10 | 19/20 | 10/15 | 12/15 | **75/91 = 82.4%** | 95.6% | 0.893 | 47 |
| rerank | 27/31 | 5/10 | 18/20 | 14/15 | 12/15 | **76/91 = 83.5%** | 97.8% | 0.903 | 779 |
| loc | 25/31 | 9/10 | 18/20 | 11/15 | 14/15 | **77/91 = 84.6%** | 94.5% | 0.897 | 59 |
| rerank+loc | 27/31 | 7/10 | 20/20 | 15/15 | 14/15 | **83/91 = 91.2%** | 98.9% | 0.947 | 887 |
| rerank-top10+loc | 27/31 | 7/10 | 20/20 | 15/15 | 14/15 | **83/91 = 91.2%** | 98.9% | 0.947 | 884 |
| hybrid | 25/31 | 6/10 | 18/20 | 11/15 | 10/15 | **70/91 = 76.9%** | 94.5% | 0.857 | 45 |
| hybrid+rerank | 27/31 | 5/10 | 18/20 | 14/15 | 12/15 | **76/91 = 83.5%** | 97.8% | 0.903 | 854 |
| hybrid+rerank+loc | 27/31 | 7/10 | 20/20 | 15/15 | 14/15 | **83/91 = 91.2%** | 98.9% | 0.947 | 861 |

McNemar chính xác trên top-1, gộp 91 câu dev:

- vector vs rerank+loc: chỉ vector đúng 3, chỉ rerank+loc đúng 11, p = 0.057
- rerank vs rerank+loc: chỉ rerank đúng 0, chỉ rerank+loc đúng 7, p = 0.016
- loc vs rerank+loc: chỉ loc đúng 4, chỉ rerank+loc đúng 10, p = 0.180
- vector vs rerank: chỉ vector đúng 8, chỉ rerank đúng 9, p = 1.000
- vector vs hybrid: chỉ vector đúng 10, chỉ hybrid đúng 5, p = 0.302
- rerank vs hybrid+rerank: chỉ rerank đúng 0, chỉ hybrid+rerank đúng 0, p = 1.000
- rerank+loc vs hybrid+rerank+loc: chỉ rerank+loc đúng 0, chỉ hybrid+rerank+loc đúng 0, p = 1.000
