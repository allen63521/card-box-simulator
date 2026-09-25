# 2026 Topps Chrome Baseball 拆盒模擬器

解壓縮 ZIP，直接以瀏覽器開啟 index.html。不需安裝、不需網路；所有配套檔案請留在同一資料夾。

選擇盒型後，可點卡包或「開下一包」，也可「一次開完」。滑鼠移至卡片或用 Tab 聚焦即可查看完整姓名、卡號、球隊、卡種及 1:X 機率。完成後顯示全部卡片，依機率分母由高到低排序，Base 最後。AUTO 代表簽名，RC 來自卡表 Rookie 標記或 Rookie 系列。

盒型：Hobby 20×4／至少 1 簽；Jumbo 12×11／至少 2 簽；Value 7×4；Mega 6×7；Delight 1×12／至少 2 簽。
盒型核實來源：https://ripped.topps.com/2026-topps-chrome-baseball-box-comparison/
Mega 另核對：https://www.topps.com/products/2026-topps-chrome%C2%AE-baseball-mega-box

資料來源：使用者提供的 2026_Topps_Chrome_Baseball_Checklist_Final_7.22.pdf 與 2026_Topps_Chrome_Baseball_Odds.pdf。原始 PDF 未修改。
共 343 筆機率、55 個卡表系列、1,643 筆球員列；同一卡號的雙人卡合併後為 1,629 個卡表項目，含 300 張 Base。全部 odds 均對應至系列，無 Base 回退。詳見 extraction-report.json。

模型：每個有效 odds 列各做一次獨立 Bernoulli 抽樣；超過包內張數時優先保留稀有卡，剩餘位置用 Base 補足。只對自然簽名不足的盒補到最低保證，以該盒型各簽名列的相對機率加權選擇，替換 Base；因此保證後平均簽名數會高於自然 odds 期望。UI 的自然期望值為容量截斷與補保證前。若極端抽樣無足夠 Base 可補保證，重新產生該盒。官方未公開工廠裝箱相關性，這是近似模擬。球員在各系列均勻抽取，平行版本沿用母系列名單；不推定印量、實際編號或球員個別概率。

已處理跨行名稱及 PDF 分頁溢出的 Rookie 欄（33–63 頁接回 1–31 頁），保留不同卡號的重複球員。
來源異常：2025 WORLD SERIES CHAMPIONS AUTOGRAPHS GOLD REFRACTOR 的 Hobby「1:1,2175」和 Delight「0.39374999999999999」格式異常，僅排除這兩個格子，其餘欄位保留。沒有略過其他機率列。Fanatics 的 odds 保留於資料，尚未核實專屬盒型規格，故未開放盒型。

驗證：五種盒型 UI 開盒張數皆正確；單包、整盒、重新開盒、完成對話框、鍵盤卡片詳情及排序通過；桌面 1440×1000 與手機 390×844 視覺檢查，手機无水平溢出，測試時無相關 console 錯誤。另模擬 1,000 盒／盒型，共 5,000 盒，包數、每包張數及最低簽名保證皆通過。僅於 Codex 內建瀏覽器完成 UI 測試，未逐一測試所有瀏覽器。
