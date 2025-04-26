document.addEventListener('DOMContentLoaded', function() {
    fetchHistory();
});

async function fetchHistory() {
    const accordionContainer = document.getElementById('history-accordion');
    accordionContainer.innerHTML = '<div class="text-center p-3">履歴を読み込み中...</div>'; // ローディング表示

    try {
        const response = await fetch('/api/report_history');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const historyData = await response.json();

        if (historyData.length === 0) {
            accordionContainer.innerHTML = '<div class="text-center p-3">報告履歴はありません。</div>';
            return;
        }

        // 年月でグループ化
        const groupedHistory = historyData.reduce((acc, record) => {
            const reportedDate = new Date(record.reported_at);
            // reported_at は UTC で保存されていると仮定し、JSTに変換して年月を取得
            const year = reportedDate.getFullYear();
            const month = reportedDate.getMonth() + 1; // getMonthは0始まり
            const yearMonth = `${year}年${String(month).padStart(2, '0')}月`;

            if (!acc[yearMonth]) {
                acc[yearMonth] = [];
            }
            acc[yearMonth].push(record);
            return acc;
        }, {});

        // アコーディオン要素を生成
        accordionContainer.innerHTML = ''; // ローディング表示をクリア
        const sortedYearMonths = Object.keys(groupedHistory).sort().reverse(); // 新しい年月を上に

        sortedYearMonths.forEach((yearMonth, index) => {
            const records = groupedHistory[yearMonth];
            const accordionItemId = `collapse-${index}`;
            const isFirstItem = index === 0; // 最初の項目をデフォルトで開く

            const accordionItem = document.createElement('div');
            accordionItem.classList.add('accordion-item');
            accordionItem.innerHTML = `
                <h2 class="accordion-header" id="heading-${index}">
                    <button class="accordion-button ${isFirstItem ? '' : 'collapsed'}" type="button" data-bs-toggle="collapse" data-bs-target="#${accordionItemId}" aria-expanded="${isFirstItem}" aria-controls="${accordionItemId}">
                        ${yearMonth} (${records.length}件)
                    </button>
                </h2>
                <div id="${accordionItemId}" class="accordion-collapse collapse ${isFirstItem ? 'show' : ''}" aria-labelledby="heading-${index}" data-bs-parent="#history-accordion">
                    <div class="accordion-body">
                        <table class="table table-sm table-hover">
                            <thead>
                                <tr>
                                    <th>報告日時 (JST)</th>
                                    <th>スケジュール名</th>
                                    <th>スケジュールID</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${records.map(record => {
                                    // reported_at を JST で表示
                                    const reportedDateJST = new Date(record.reported_at).toLocaleString('ja-JP', { timeZone: 'Asia/Tokyo' });
                                    return `
                                        <tr>
                                            <td>${reportedDateJST}</td>
                                            <td>${record.schedule_description}</td>
                                            <td>${record.schedule_id}</td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
            accordionContainer.appendChild(accordionItem);
        });

    } catch (error) {
        console.error('Error fetching history:', error);
        accordionContainer.innerHTML = '<div class="alert alert-danger">履歴の読み込み中にエラーが発生しました。</div>';
    }
}
