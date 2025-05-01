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
            scheduleListBody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">スケジュールの読み込みに失敗しました。</td></tr>';
        }
    }

    // --- スケジュール描画 --- 
    function renderSchedules(schedules) {
        scheduleListBody.innerHTML = ''; // 一旦クリア
        if (schedules.length === 0) {
            scheduleListBody.innerHTML = '<tr><td colspan="8" class="text-center">登録されているスケジュールはありません。</td></tr>';
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
                    <button class="btn btn-success btn-sm run-now-button" data-schedule-id="${schedule.id}" data-is-active="${schedule.is_active}">即時報告</button>
                    <button class="btn btn-warning btn-sm edit-button" data-schedule-id="${schedule.id}" data-bs-toggle="modal" data-bs-target="#editScheduleModal">編集</button>
                    <button class="btn btn-danger btn-sm delete-button" data-schedule-id="${schedule.id}">削除</button>
                    <button class="btn ${toggleClass} btn-sm toggle-active-button" data-schedule-id="${schedule.id}" data-is-active="${schedule.is_active}">${toggleButtonText}</button>
                </td>
                <td>
                    <button class="btn btn-info btn-sm report-completed-button" data-schedule-id="${schedule.id}">報告完了</button>
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
                    document.getElementById('edit-excel-path').value = schedule.excel_path || ''; // IDを修正
                    document.getElementById('edit_google_form_url').value = schedule.google_form_url || '';
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
            const isActive = button.dataset.isActive === 'true'; // Get status from the button
            console.log("Run now button action for", scheduleId, "Is Active:", isActive); // Debug log

            // Check if active BEFORE showing confirm dialog
            if (!isActive) {
                alert('タスクが有効化されていません。有効化してから報告してください。');
                return; // Stop further execution
            }

            // Only show confirm if active
            if (confirm(`スケジュール ID: ${scheduleId} の報告を即時実行しますか？`)) {
                 console.log("Confirmed run now. Sending fetch request..."); // ★デバッグログ追加
                 // --- Add fetch call --- 
                 fetch(`${API_BASE}/${scheduleId}/run_now`, {
                    method: 'POST',
                    headers: {
                        // No Content-Type needed for empty body, but CSRF might be needed later
                    }
                    // No body needed for this request
                 })
                 .then(response => {
                     if (!response.ok) {
                         // Try to parse error message from backend if possible
                         return response.json().then(err => { 
                             throw new Error(err.message || `HTTP error! Status: ${response.status}`); 
                         }).catch(() => {
                             // Fallback if response is not JSON or parsing fails
                              throw new Error(`HTTP error! Status: ${response.status}`);
                         });
                     }
                     return response.json(); // Expecting {status: 'success', ...} or similar
                 })
                 .then(data => {
                     console.log("Run now successful:", data);
                     alert(`スケジュール ${scheduleId} の即時報告を開始しました。`); 
                     // Optionally, reload schedules or update UI if needed, but history is main goal
                     // loadSchedules(); 
                 })
                 .catch(error => {
                     console.error('Error running schedule now:', error);
                     alert(`即時報告の開始に失敗しました: ${error.message}`);
                 });
            }
        }
        // 報告完了ボタン
        else if (target.classList.contains('report-completed-button')) {
            console.log("Report completed button action for", scheduleId);
            if (confirm(`スケジュール ID: ${scheduleId} の報告を完了として記録しますか？`)) {
                fetch(`/api/schedules/${scheduleId}/report_completed`, { method: 'POST' })
                    .then(response => {
                        if (!response.ok) {
                            return response.json().then(err => { throw new Error(err.message || `HTTP error! status: ${response.status}`) });
                        }
                        return response.json();
                    })
                    .then(data => {
                        alert(data.message || '報告完了を記録しました。');
                        // ボタンを無効化するなど、UIフィードバックを追加しても良い
                        // target.disabled = true;
                        // target.textContent = '記録済み';
                        // 必要に応じてリストを再読み込み loadSchedules();
                    })
                    .catch(error => {
                        console.error('Error marking report as completed:', error);
                        alert(`報告完了の記録に失敗しました: ${error.message}`);
                    });
            }
        }

    });

    // --- 編集モーダルの保存ボタン --- 
    saveEditButton.addEventListener('click', async function() {
        const id = document.getElementById('edit-schedule-id').value;
        const description = document.getElementById('edit-description').value;
        const interval_minutes = parseInt(document.getElementById('edit-interval_minutes').value, 10);
        const excel_path = document.getElementById('edit-excel-path').value; // IDを修正
        const google_form_url = document.getElementById('edit_google_form_url').value;

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

    // --- Server-Sent Events (SSE) Setup ---
    console.log('Setting up SSE connection...');
    const eventSource = new EventSource('/stream'); // Connect to the SSE endpoint

    eventSource.onopen = function() {
        console.log('SSE connection established.');
    };

    eventSource.onerror = function(err) {
        console.error('SSE error:', err);
        // Optionally attempt to reconnect or notify the user
    };

    // Listen for 'alert_triggered' events from the server
    eventSource.addEventListener('alert_triggered', function(event) {
        console.log('Received alert_triggered event:', event.data);
        try {
            const data = JSON.parse(event.data);
            const scheduleId = data.schedule_id;

            if (scheduleId) {
                // Find the table row corresponding to the schedule ID
                const row = scheduleListBody.querySelector(`tr[data-schedule-id='${scheduleId}']`);
                if (row) {
                    // Find the cell for report status in that row
                    const reportStatusCell = row.querySelector('.report-status-cell');
                    if (reportStatusCell) {
                        // Update the cell content with the 'Report Incomplete' button
                        reportStatusCell.innerHTML = `
                            <button class="btn btn-sm btn-danger report-completed-button" data-schedule-id="${scheduleId}">
                                報告未完了
                            </button>
                        `;
                        console.log(`Updated report status for schedule ${scheduleId} to 'Incomplete'`);
                    } else {
                        console.error(`Could not find report status cell for schedule ${scheduleId}`);
                    }
                } else {
                    console.warn(`Could not find table row for schedule ${scheduleId}`);
                }
            } else {
                 console.error('Received alert_triggered event without schedule_id:', data);
            }
        } catch (e) {
            console.error('Error parsing SSE data:', e);
        }
    });

    // --- Edit, Delete, Toggle Active, Open Form --- 
    scheduleListBody.addEventListener('click', function(event) {
        const target = event.target;
        // Use closest to handle clicks inside the button (e.g., on text)
        const reportButton = target.closest('.mark-complete-btn');
        const editButton = target.closest('.edit-btn');
        const deleteButton = target.closest('.delete-btn');
        const toggleButton = target.closest('.toggle-active-btn');
        const openFormButton = target.closest('.open-form-btn');

        // Edit Button
        if (editButton) {
            const scheduleId = editButton.getAttribute('data-id');
            fetch(`/api/schedules/${scheduleId}`)
                .then(response => response.json())
                .then(schedule => {
                    document.getElementById('edit-schedule-id').value = schedule.id;
                    document.getElementById('edit-description').value = schedule.name;
                    document.getElementById('edit-interval_minutes').value = schedule.interval_minutes;
                    document.getElementById('edit-excel-path').value = schedule.excel_path || '';
                    document.getElementById('edit-google_form_url').value = schedule.google_form_url || '';
                    editModal.show(); // Show modal programmatically
                })
                .catch(error => console.error('Error fetching schedule details:', error));
        }

        // Delete Button
        else if (deleteButton) {
            const scheduleId = deleteButton.getAttribute('data-id');
            if (confirm('本当にこのスケジュールを削除しますか？')) {
                fetch(`/api/schedules/${scheduleId}`, {
                    method: 'DELETE',
                })
                .then(response => {
                     if (!response.ok) {
                        return response.json().then(err => { throw new Error(err.error || 'スケジュールの削除に失敗しました。'); });
                    }
                    return response.json();
                })
                .then(() => fetchSchedules()) // Refresh list
                .catch(error => {
                    console.error('Error deleting schedule:', error);
                    alert(`エラー: ${error.message}`);
                });
            }
        }

        // Toggle Active/Inactive Button
        else if (toggleButton) {
            const scheduleId = toggleButton.getAttribute('data-id');
            fetch(`/api/schedules/${scheduleId}/toggle_active`, {
                method: 'POST',
            })
             .then(response => {
                 if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.error || '状態の切り替えに失敗しました。'); });
                }
                return response.json();
            })
            .then(() => fetchSchedules()) // Refresh list
            .catch(error => {
                console.error('Error toggling schedule active state:', error);
                alert(`エラー: ${error.message}`);
            });
        }
        
        // Open Google Form Button
        else if (openFormButton) {
            const formUrl = openFormButton.getAttribute('data-url');
            if (formUrl) {
                fetch(`/api/open_form`, { 
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url: formUrl }),
                 })
                .then(response => {
                    if (!response.ok) {
                       return response.json().then(err => { throw new Error(err.error || 'フォームを開けませんでした。'); });
                   }
                   return response.json();
               })
               .then(data => {
                    if(data.success) {
                        console.log('Form open request sent successfully.');
                        // Optional: Provide feedback to the user
                    }
               })
               .catch(error => {
                   console.error('Error opening form:', error);
                   alert(`エラー: ${error.message}`);
                });
            }
        }

        // --- Report Completion Button --- 
        else if (reportButton) { // Use the variable defined earlier
            const scheduleId = reportButton.getAttribute('data-id');
            reportButton.disabled = true; // Prevent double clicks
            reportButton.textContent = '処理中...';

            fetch(`/api/schedules/${scheduleId}/mark_completed`, {
                method: 'POST',
            })
            .then(response => {
                if (!response.ok) {
                    // Try to parse error JSON, otherwise use status text
                    return response.json().then(err => { 
                        throw new Error(err.description || err.error || `HTTP error! status: ${response.status}`); 
                    }).catch(() => {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Update button appearance to 'Report Completed'
                    reportButton.classList.remove('btn-danger');
                    reportButton.classList.add('btn-success');
                    reportButton.textContent = '報告完了';
                    // Keep it disabled as the action is complete
                    console.log(`Report marked complete for schedule ${scheduleId}`);
                } else {
                    // This case might not be reached if errors are thrown above
                    throw new Error(data.description || data.error || 'サーバーエラーが発生しました。');
                }
            })
            .catch(error => {
                console.error('Error marking report complete:', error);
                alert(`報告完了エラー: ${error.message}`);
                // Re-enable button and revert text on error
                reportButton.disabled = false;
                reportButton.textContent = '報告未完了';
                // Ensure it has the danger class if it failed
                reportButton.classList.remove('btn-success');
                reportButton.classList.add('btn-danger');
            });
        }
    });

});
