"""
貸出関連のビジネスロジックを管理するサービス
"""

from datetime import datetime, timedelta
from models import db, Book, User, LoanHistory, Reservation, ReservationStatus
import logging

logger = logging.getLogger(__name__)

class LoanService:
    """貸出サービスクラス"""
    
    @staticmethod
    def can_user_borrow_book(user_id, book_id=None):
        """
        ユーザーが本を借りられるかどうかを判定
        
        Args:
            user_id: ユーザーID
            book_id: 本のID（オプション）
            
        Returns:
            tuple: (可否(bool), エラーメッセージ(str))
        """
        user = User.query.get(user_id)
        if not user:
            return False, "ユーザーが見つかりません"
        
        # 延滞中の本があるかチェック
        if user.has_overdue_books():
            return False, "延滞中の本があるため、新しい本を借りることができません。まず延滞本を返却してください。"
        
        # 貸出上限チェック
        if not user.can_borrow_more():
            current_total = user.current_loan_count() + user.current_reservation_count()
            return False, f"貸出上限({user.max_loan_limit}冊)に達しています。現在: 貸出中{user.current_loan_count()}冊 + 予約中{user.current_reservation_count()}冊 = {current_total}冊"
        
        # 特定の本が指定されている場合、その本の状態をチェック
        if book_id:
            book = Book.query.get(book_id)
            if not book:
                return False, "指定された本が見つかりません"
            
            if not book.is_available:
                return False, "この本は現在貸出不可となっています"
            
            if book.borrower_id:
                return False, "この本は既に他のユーザーに貸し出されています"
        
        return True, ""
    
    @staticmethod
    def borrow_book(user_id, book_id, due_date=None):
        """
        本を貸し出す
        
        Args:
            user_id: ユーザーID
            book_id: 本のID
            due_date: 返却期限日（指定なしの場合は2週間後）
            
        Returns:
            tuple: (成功(bool), メッセージ(str), 貸出履歴ID(int|None))
        """
        # 貸出可能性チェック
        can_borrow, error_msg = LoanService.can_user_borrow_book(user_id, book_id)
        if not can_borrow:
            return False, error_msg, None
        
        user = User.query.get(user_id)
        book = Book.query.get(book_id)
        
        # 返却期限の設定（デフォルト2週間）
        if due_date is None:
            due_date = datetime.utcnow() + timedelta(weeks=2)
        
        try:
            # 本の状態を更新
            book.borrower_id = user_id
            book.status = 'ON_LOAN'
            
            # 貸出履歴を作成
            loan_history = LoanHistory(
                book_id=book_id,
                book_title=book.title,
                borrower_id=user_id,
                loan_date=datetime.utcnow(),
                due_date=due_date
            )
            
            db.session.add(loan_history)
            
            # 予約があった場合、最初の予約者に通知
            pending_reservations = Reservation.query.filter_by(
                book_id=book_id,
                status=ReservationStatus.PENDING
            ).order_by(Reservation.reservation_date).all()
            
            if pending_reservations:
                # 最初の予約が自分の予約の場合、それを満たす
                first_reservation = pending_reservations[0]
                if first_reservation.user_id == user_id:
                    first_reservation.status = ReservationStatus.FULFILLED
                    logger.info(f"予約が満たされました - Book: {book.title}, User: {user.email}")
            
            db.session.commit()
            
            logger.info(f"本が貸し出されました - Book: {book.title}, User: {user.email}, Due: {due_date}")
            return True, f"「{book.title}」を貸し出しました。返却期限: {due_date.strftime('%Y年%m月%d日')}", loan_history.id
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"貸出処理でエラーが発生しました: {e}")
            return False, "貸出処理中にエラーが発生しました", None
    
    @staticmethod
    def return_book(loan_history_id):
        """
        本を返却する
        
        Args:
            loan_history_id: 貸出履歴ID
            
        Returns:
            tuple: (成功(bool), メッセージ(str))
        """
        loan_history = LoanHistory.query.get(loan_history_id)
        if not loan_history:
            return False, "貸出履歴が見つかりません"
        
        if loan_history.return_date:
            return False, "この本は既に返却済みです"
        
        try:
            # 返却処理
            loan_history.return_date = datetime.utcnow()
            
            # 本の状態を更新
            book = loan_history.book
            book.borrower_id = None
            
            # 予約者がいるかチェック
            pending_reservations = Reservation.query.filter_by(
                book_id=book.id,
                status=ReservationStatus.PENDING
            ).order_by(Reservation.reservation_date).all()
            
            if pending_reservations:
                # 最初の予約者に通知
                first_reservation = pending_reservations[0]
                first_reservation.status = ReservationStatus.NOTIFIED
                first_reservation.notification_sent_at = datetime.utcnow()
                book.status = 'RESERVED'
                logger.info(f"予約者に通知しました - Book: {book.title}, User: {first_reservation.user.email}")
            else:
                # 予約者がいない場合は利用可能に
                book.status = 'AVAILABLE'
            
            db.session.commit()
            
            logger.info(f"本が返却されました - Book: {book.title}, User: {loan_history.borrower.email}")
            return True, f"「{book.title}」を返却しました"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"返却処理でエラーが発生しました: {e}")
            return False, "返却処理中にエラーが発生しました"
    
    @staticmethod
    def extend_loan(loan_history_id, extension_weeks=1):
        """
        貸出期間を延長する
        
        Args:
            loan_history_id: 貸出履歴ID
            extension_weeks: 延長週数（1 or 2）
            
        Returns:
            tuple: (成功(bool), メッセージ(str))
        """
        loan_history = LoanHistory.query.get(loan_history_id)
        if not loan_history:
            return False, "貸出履歴が見つかりません"
        
        if loan_history.return_date:
            return False, "この本は既に返却済みです"
        
        # 延長可能性チェック
        if not loan_history.can_extend():
            if loan_history.extension_count >= 1:
                return False, "既に延長回数の上限(1回)に達しています"
            
            # 予約者がいる場合
            active_reservations = [r for r in loan_history.book.reservations if r.status == ReservationStatus.PENDING]
            if active_reservations:
                return False, "この本には予約者がいるため延長できません"
        
        try:
            # 延長処理
            loan_history.due_date = loan_history.due_date + timedelta(weeks=extension_weeks)
            loan_history.extension_count += 1
            loan_history.extended_date = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"貸出期間が延長されました - Book: {loan_history.book.title}, User: {loan_history.borrower.email}, New due: {loan_history.due_date}")
            return True, f"「{loan_history.book.title}」の返却期限を{extension_weeks}週間延長しました。新しい返却期限: {loan_history.due_date.strftime('%Y年%m月%d日')}"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"延長処理でエラーが発生しました: {e}")
            return False, "延長処理中にエラーが発生しました"
    
    @staticmethod
    def get_user_active_loans(user_id):
        """
        ユーザーの現在の貸出一覧を取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            list: 貸出履歴のリスト
        """
        return LoanHistory.query.filter_by(
            borrower_id=user_id,
            return_date=None
        ).order_by(LoanHistory.due_date).all()
    
    @staticmethod
    def get_overdue_loans():
        """
        延滞中の貸出一覧を取得
        
        Returns:
            list: 延滞中の貸出履歴のリスト
        """
        now = datetime.utcnow()
        return LoanHistory.query.filter(
            LoanHistory.return_date.is_(None),
            LoanHistory.due_date < now
        ).order_by(LoanHistory.due_date).all()
    
    @staticmethod
    def get_due_soon_loans(days=3):
        """
        返却期限が近い貸出一覧を取得
        
        Args:
            days: 何日以内かを指定（デフォルト3日）
            
        Returns:
            list: 返却期限が近い貸出履歴のリスト
        """
        now = datetime.utcnow()
        due_threshold = now + timedelta(days=days)
        
        return LoanHistory.query.filter(
            LoanHistory.return_date.is_(None),
            LoanHistory.due_date >= now,
            LoanHistory.due_date <= due_threshold
        ).order_by(LoanHistory.due_date).all()