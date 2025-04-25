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
            row.innerHTML = `
                <td>${schedule.id}</td>
                <td>${escapeHtml(schedule.description)}</td>
                <td>${schedule.interval_minutes ?? 'N/A'}</td>
                <td>${escapeHtml(schedule.excel_path) || '-'}</td>
                <td>${schedule.google_form_url ? `<a href="${schedule.google_form_url}" target="_blank">Link</a>` : ''}</td>
                <td>
                    <span class="badge ${schedule.is_active ? 'bg-success' : 'bg-secondary'}">
                        ${schedule.is_active ? '有効' : '無効'}
                    </span>
                </td>
                <td class="action-buttons">
                    <button class="btn btn-sm btn-warning edit-btn" data-id="${schedule.id}" data-description="${escapeHtml(schedule.description)}" data-interval="${schedule.interval_minutes ?? ''}" data-active="${schedule.is_active}" data-excel-path="${escapeHtml(schedule.excel_path)}" data-google-form-url="${schedule.google_form_url}">編集</button>
                    <button class="btn btn-sm ${schedule.is_active ? 'btn-secondary' : 'btn-success'} toggle-btn" data-id="${schedule.id}" data-active="${schedule.is_active}">${schedule.is_active ? '無効化' : '有効化'}</button>
                    <button class="btn btn-sm btn-danger delete-btn" data-id="${schedule.id}">削除</button>
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
        const scheduleId = target.dataset.id;

        // 編集ボタン
        if (target.classList.contains('edit-btn')) {
            document.getElementById('edit-schedule-id').value = scheduleId;
            document.getElementById('edit-description').value = target.dataset.description;
            document.getElementById('edit-interval_minutes').value = target.dataset.interval;
            document.getElementById('edit-excel_path').value = target.dataset.excelPath;
            document.getElementById('edit-google_form_url').value = target.dataset.googleFormUrl;
            editModal.show();
        }

        // 有効/無効 切り替えボタン
        if (target.classList.contains('toggle-btn')) {
            const currentStatus = target.dataset.active === 'true';
            try {
                const response = await fetch(`${API_BASE}/${scheduleId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ is_active: !currentStatus }), // ステータスを反転
                });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                }
                loadSchedules();
            } catch (error) {
                console.error('Error toggling schedule status:', error);
                 alert(`状態の切り替えに失敗しました: ${error.message}`);
            }
        }

        // 削除ボタン
        if (target.classList.contains('delete-btn')) {
            if (confirm(`本当にスケジュール ID: ${scheduleId} を削除しますか？`)) {
                try {
                    const response = await fetch(`${API_BASE}/${scheduleId}`, {
                        method: 'DELETE',
                    });
                    if (!response.ok) {
                         const errorData = await response.json();
                         throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                    }
                    loadSchedules();
                } catch (error) {
                    console.error('Error deleting schedule:', error);
                    alert(`スケジュールの削除に失敗しました: ${error.message}`);
                }
            }
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
