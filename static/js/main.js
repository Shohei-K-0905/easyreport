document.addEventListener('DOMContentLoaded', function() {
    const scheduleListBody = document.getElementById('schedule-list');
    const addForm = document.getElementById('add-schedule-form');
    const editForm = document.getElementById('edit-schedule-form');
    const editModalElement = document.getElementById('editModal');
    const editModal = new bootstrap.Modal(editModalElement);
    const saveEditButton = document.getElementById('save-edit-button');

    // --- API エンドポイント ---
    const API_BASE = '/api/schedules';

    // --- スケジュール読み込み --- 
    async function loadSchedules() {
        try {
            const response = await fetch(API_BASE);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const schedules = await response.json();
            renderSchedules(schedules);
        } catch (error) {
            console.error('Error loading schedules:', error);
            scheduleListBody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">スケジュールの読み込みに失敗しました。</td></tr>';
        }
    }

    // --- スケジュール描画 --- 
    function renderSchedules(schedules) {
        scheduleListBody.innerHTML = ''; // 一旦クリア
        if (schedules.length === 0) {
            scheduleListBody.innerHTML = '<tr><td colspan="7" class="text-center">登録されているスケジュールはありません。</td></tr>';
            return;
        }

        schedules.forEach(schedule => {
            const row = document.createElement('tr');
            const isActiveText = schedule.is_active ? '有効' : '無効';
            const toggleClass = schedule.is_active ? 'btn-secondary' : 'btn-success';
            const toggleButtonText = schedule.is_active ? '無効化' : '有効化';

            row.innerHTML = `
                <td>${schedule.id}</td>
                <td>${escapeHtml(schedule.description)}</td>
                <td>${schedule.interval_minutes ?? 'N/A'}</td>
                <td>${escapeHtml(schedule.excel_path) || '-'}</td>
                <td>${schedule.google_form_url ? `<a href="${schedule.google_form_url}" target="_blank">Link</a>` : ''}</td>
                <td>${isActiveText}</td>
                <td>
                    <button class="btn btn-success btn-sm run-now-button" data-schedule-id="${schedule.id}">即時報告</button>
                    <button class="btn btn-warning btn-sm edit-button" data-schedule-id="${schedule.id}" data-bs-toggle="modal" data-bs-target="#editScheduleModal">編集</button>
                    <button class="btn btn-danger btn-sm delete-button" data-schedule-id="${schedule.id}">削除</button>
                    <button class="btn ${toggleClass} btn-sm toggle-active-button" data-schedule-id="${schedule.id}" data-is-active="${schedule.is_active}">${toggleButtonText}</button>
                </td>
            `;
            scheduleListBody.appendChild(row);
        });
    }

    // --- スケジュール追加処理 --- 
    addForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        const description = document.getElementById('description').value;
        const interval_minutes = parseInt(document.getElementById('interval_minutes').value, 10);
        const excel_path = document.getElementById('excel_path').value;
        const google_form_url = document.getElementById('google_form_url').value;

        // Basic validation
        if (isNaN(interval_minutes) || interval_minutes <= 0) {
            alert('Please enter a valid interval in minutes (must be greater than 0).');
            return;
        }

        try {
            const response = await fetch(API_BASE, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ description, interval_minutes, excel_path, google_form_url }),
            });
            if (!response.ok) {
                 const errorData = await response.json();
                 throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
            addForm.reset(); // フォームリセット
            loadSchedules(); // リスト再読み込み
        } catch (error) {
            console.error('Error adding schedule:', error);
            alert(`スケジュールの追加に失敗しました: ${error.message}`);
        }
    });

    // --- 編集・有効/無効・削除ボタンのイベントリスナー (イベント委任) --- 
    scheduleListBody.addEventListener('click', async function(event) {
        const target = event.target;
        // data-schedule-id 属性を持つ最も近い親要素(ボタン)を探す
        const button = target.closest('[data-schedule-id]');

        if (!button) {
            // クリックされた要素またはその親に data-schedule-id がなければ何もしない
             // console.log("Clicked element doesn't have schedule-id:", target);
            return;
        }

        const scheduleId = button.dataset.scheduleId;
        console.log("Button clicked! Schedule ID:", scheduleId, "Target classes:", target.classList); // デバッグログ追加

        // 削除ボタン
        if (target.classList.contains('delete-button')) {
             console.log("Delete button action for", scheduleId); // デバッグログ
            if (confirm(`本当にスケジュール ID: ${scheduleId} を削除しますか？`)) {
                try {
                    fetch(`${API_BASE}/${scheduleId}`, {
                        method: 'DELETE',
                    })
                    .then(response => {
                        if (!response.ok) {
                             return response.json().then(err => { throw new Error(err.error || '削除に失敗しました') });
                        }
                        return response.json(); // 削除成功時もjsonを返す想定
                    })
                    .then(() => {
                        loadSchedules(); // リストを再読み込み
                    })
                    .catch(error => {
                        console.error('Error deleting schedule:', error);
                        alert(`スケジュールの削除に失敗しました: ${error.message}`);
                    });
                } catch (error) {
                    console.error('Error in delete fetch setup:', error);
                    alert('削除リクエストの設定中にエラーが発生しました。');
                }
            }
        }
        // 編集ボタン
        else if (target.classList.contains('edit-button')) {
            console.log("Edit button action for", scheduleId); // デバッグログ
            // 編集モーダルにデータを設定 (既存のスケジュールデータを取得してモーダルに表示する処理は editScheduleModal.show() の前にあるべき)
            fetch(`/api/schedules/${scheduleId}`) // 個別取得APIを叩く
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Schedule data fetch failed');
                    }
                    return response.json();
                })
                .then(schedule => {
                    document.getElementById('edit-schedule-id').value = schedule.id;
                    document.getElementById('edit-description').value = schedule.description || '';
                    document.getElementById('edit-interval_minutes').value = schedule.interval_minutes || '';
                    document.getElementById('edit-excel_path').value = schedule.excel_path || '';
                    document.getElementById('edit-google_form_url').value = schedule.google_form_url || '';
                    document.getElementById('edit-is_active').checked = schedule.is_active;
                    // Bootstrap 5 のモーダル表示方法
                     const modalElement = document.getElementById('editScheduleModal');
                     const modal = bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
                     modal.show();
                })
                .catch(error => {
                    console.error('Error fetching schedule for edit:', error);
                    alert('編集データの取得に失敗しました。');
                });
        }
        // アクティブ/非アクティブ切り替えボタン
        else if (target.classList.contains('toggle-active-button')) {
            console.log("Toggle active button action for", scheduleId); // デバッグログ
            const currentStatus = button.dataset.isActive === 'true'; // buttonから取得
            const newStatus = !currentStatus;
            try {
                 fetch(`${API_BASE}/${scheduleId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ is_active: newStatus }),
                })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(err => { throw new Error(err.error || '状態の切り替えに失敗しました') });
                    }
                    return response.json();
                })
                .then(() => {
                    loadSchedules(); // リストを再読み込み
                })
                .catch(error => {
                    console.error('Error toggling schedule active state:', error);
                    alert(`スケジュールの状態切り替えに失敗しました: ${error.message}`);
                });
            } catch (error) {
                console.error('Error in toggle active fetch setup:', error);
                alert('状態切り替えリクエストの設定中にエラーが発生しました。');
            }
        }
        // 即時報告ボタン
        else if (target.classList.contains('run-now-button')) {
            console.log("Run now button action for", scheduleId); // ★デバッグログ追加
            if (confirm(`スケジュール ID: ${scheduleId} の報告を即時実行しますか？`)) {
                 console.log("Confirmed run now. Sending fetch request..."); // ★デバッグログ追加
                // バックエンドに即時実行リクエストを送る
                fetch(`/api/schedules/${scheduleId}/run_now`, { method: 'POST' })
                    .then(response => {
                         console.log("Fetch response received:", response.status); // ★デバッグログ追加
                        if (!response.ok) {
                           // エラーメッセージをサーバーから取得試行
                            console.error("Fetch error status:", response.status);
                            return response.json().then(err => {
                                console.error("Error details from server:", err);
                                throw new Error(err.error || 'Immediate run failed')
                            });
                        }
                        return response.json();
                    })
                    .then(data => {
                        // 成功した場合（任意でメッセージ表示）
                        console.log("Run now successful:", data); // ★デバッグログ追加
                        alert(`スケジュール ID: ${scheduleId} の即時報告を開始しました。 (${data.message || ''})`);
                    })
                    .catch(error => {
                        console.error('Error running schedule now:', error); // ★デバッグログ追加
                        alert(`即時報告の実行に失敗しました: ${error.message}`);
                    });
            } else {
                 console.log("Run now cancelled by user."); // ★デバッグログ追加
            }
        } else {
             console.log("Clicked button doesn't match known actions:", target.classList);
        }
    });

    // --- 編集モーダルの保存ボタン --- 
    saveEditButton.addEventListener('click', async function() {
        const id = document.getElementById('edit-schedule-id').value;
        const description = document.getElementById('edit-description').value;
        const interval_minutes = parseInt(document.getElementById('edit-interval_minutes').value, 10);
        const excel_path = document.getElementById('edit-excel_path').value;
        const google_form_url = document.getElementById('edit-google_form_url').value;

        // Basic validation
        if (isNaN(interval_minutes) || interval_minutes <= 0) {
            alert('Please enter a valid interval in minutes (must be greater than 0).');
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ description, interval_minutes, excel_path, google_form_url }),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
            editModal.hide();
            loadSchedules();
        } catch (error) {
            console.error('Error updating schedule:', error);
            alert(`スケジュールの更新に失敗しました: ${error.message}`);
        }
    });

    // --- 初期読み込み --- 
    loadSchedules();

    // --- ヘルパー関数 --- 
    function escapeHtml(unsafe) {
        if (unsafe === null || typeof unsafe === 'undefined') {
            return '';
        }
        return unsafe
             .toString()
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
     }

});
