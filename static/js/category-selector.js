/**
 * 動的カテゴリ選択機能
 * 第1分類の選択に応じて第2分類の選択肢を動的に更新
 */
document.addEventListener('DOMContentLoaded', function() {
    const category1Select = document.getElementById('category1');
    const category2Select = document.getElementById('category2');
    const locationSelect = document.getElementById('location');
    const form = document.querySelector('form');
    
    if (!category1Select || !category2Select) {
        return; // 要素が存在しない場合は何もしない
    }
    
    // フォーム送信時の検証
    let category2Loaded = false;
    let locationLoaded = false;
    
    // 第1分類が変更されたときの処理
    category1Select.addEventListener('change', function() {
        const selectedCategory1 = this.value;
        
        // 第2分類をリセット
        category2Select.innerHTML = '<option value="">選択してください</option>';
        
        if (selectedCategory1 === '') {
            // 第1分類が未選択の場合は第2分類も無効化
            category2Select.disabled = true;
            return;
        }
        
        // 第2分類を有効化
        category2Select.disabled = false;
        
        // APIから第2分類の選択肢を取得
        fetch(`/api/categories/${encodeURIComponent(selectedCategory1)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // 取得した選択肢を第2分類に追加
                data.forEach(option => {
                    const optionElement = document.createElement('option');
                    optionElement.value = option.value;
                    optionElement.textContent = option.text;
                    category2Select.appendChild(optionElement);
                });
                category2Loaded = true;
            })
            .catch(error => {
                console.error('Error fetching category2 options:', error);
                // エラーの場合はデフォルトメッセージを表示
                const errorOption = document.createElement('option');
                errorOption.value = '';
                errorOption.textContent = '選択肢の読み込みに失敗しました';
                category2Select.appendChild(errorOption);
            });
    });
    
    // フォーム送信時の検証
    if (form) {
        form.addEventListener('submit', function(e) {
            // 第1分類が選択されているが第2分類の選択肢が読み込まれていない場合
            if (category1Select.value !== '' && !category2Loaded) {
                e.preventDefault();
                alert('第2分類の選択肢を読み込み中です。しばらくお待ちください。');
                return false;
            }
        });
    }
    
    // ページ読み込み時に第1分類が既に選択されている場合の処理
    if (category1Select.value !== '') {
        category1Select.dispatchEvent(new Event('change'));
    } else {
        // 第1分類が未選択の場合は第2分類を無効化
        category2Select.disabled = true;
        category2Loaded = true; // 未選択の場合は読み込み完了とみなす
    }
});