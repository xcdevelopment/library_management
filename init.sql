-- テスト用データベースと本番用データベースを作成します。
-- 文字コードを `utf8mb4` に設定して、日本語や絵文字が正しく扱えるようにします。
 
CREATE DATABASE IF NOT EXISTS `library_test` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS `library` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; 