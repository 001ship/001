import tkinter as tk
from tkinter import messagebox
import sqlite3
from contextlib import closing
import logging
import sys
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

class DatabaseManager:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        """初始化数据库表结构"""
        with closing(self.conn.cursor()) as cursor:
            cursor.execute('''CREATE TABLE IF NOT EXISTS accounts
                             (id INTEGER PRIMARY KEY, 
                              user_id INTEGER UNIQUE, 
                              balance REAL,
                              username TEXT UNIQUE)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS transactions
                             (id INTEGER PRIMARY KEY, 
                              user_id INTEGER, 
                              amount REAL,
                              transaction_type TEXT, 
                              transaction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            self.conn.commit()

    def get_balance(self, user_id):
        """获取用户余额"""
        with closing(self.conn.cursor()) as cursor:
            cursor.execute("SELECT balance FROM accounts WHERE user_id=?", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None

    def update_balance(self, user_id, new_balance):
        """更新用户余额"""
        with closing(self.conn.cursor()) as cursor:
            cursor.execute("UPDATE accounts SET balance=? WHERE user_id=?", (new_balance, user_id))
            self.conn.commit()

    def register_user(self, user_id, initial_balance=0, username=None):
        """注册新用户"""
        try:
            with closing(self.conn.cursor()) as cursor:
                cursor.execute("INSERT INTO accounts (user_id, balance, username) VALUES (?, ?, ?)", 
                               (user_id, initial_balance, username or f"user_{user_id}"))
                self.conn.commit()
                logging.info(f"用户{user_id}({username or '无名'})注册成功，初始余额：{initial_balance}")
                return True
        except sqlite3.IntegrityError:
            logging.warning(f"用户{user_id}({username or '无名'})已存在或用户名重复，注册失败")
            return False

    def add_transaction(self, user_id, amount, transaction_type):
        """添加交易记录"""
        with closing(self.conn.cursor()) as cursor:
            cursor.execute("INSERT INTO transactions (user_id, amount, transaction_type) VALUES (?, ?, ?)", 
                           (user_id, amount, transaction_type))
            self.conn.commit()

    def get_transactions(self, user_id, transaction_type):
        """查询特定类型的交易记录"""
        with closing(self.conn.cursor()) as cursor:
            cursor.execute("""
                SELECT transaction_time, amount
                FROM transactions
                WHERE user_id = ? AND transaction_type = ?
                ORDER BY transaction_time DESC
            """, (user_id, transaction_type))
            return cursor.fetchall()

class RechargeApp(tk.Tk):
    def __init__(self, db_manager):
        super().__init__()
        self.title("会员管理系统")
        self.db_manager = db_manager
        self.init_ui()

    def init_ui(self):
        self.user_id_var = tk.StringVar()
        self.balance_var = tk.StringVar(value="未知")
        self.amount_var = tk.StringVar()
        self.register_user_id_var = tk.StringVar()
        self.register_username_var = tk.StringVar()
        
        tk.Label(self, text="用户ID:").grid(row=0, column=0)
        tk.Entry(self, textvariable=self.user_id_var).grid(row=0, column=1)
        
        tk.Button(self, text="查询余额", command=self.query_balance).grid(row=1, column=0)
        tk.Label(self, text="余额:").grid(row=1, column=1)
        tk.Label(self, textvariable=self.balance_var).grid(row=1, column=2)
        
        tk.Label(self, text="充值金额:").grid(row=2, column=0)
        tk.Entry(self, textvariable=self.amount_var).grid(row=2, column=1)
        tk.Button(self, text="充值", command=self.recharge).grid(row=2, column=2)
        
        tk.Label(self, text="注册用户ID:").grid(row=3, column=0)
        tk.Entry(self, textvariable=self.register_user_id_var).grid(row=3, column=1)
        
        tk.Label(self, text="用户名:").grid(row=4, column=0)
        tk.Entry(self, textvariable=self.register_username_var).grid(row=4, column=1)
        
        tk.Button(self, text="注册用户", command=self.register_new_user).grid(row=5, column=0, columnspan=2)
        
        tk.Label(self, text="查询充值记录:").grid(row=6, column=0)
        tk.Button(self, text="查询", command=self.show_deposit_history).grid(row=6, column=1)
        
        tk.Label(self, text="查询消费记录:").grid(row=7, column=0)
        tk.Button(self, text="查询", command=self.show_spend_history).grid(row=7, column=1)
        
        self.history_text = tk.Text(self, height=10, width=50)
        self.history_text.grid(row=8, column=0, columnspan=2)

    def query_balance(self):
        user_id = self.user_id_var.get()
        balance = self.db_manager.get_balance(int(user_id))
        if balance is not None:
            self.balance_var.set(str(balance))
        else:
            messagebox.showerror("错误", "用户不存在")
            self.balance_var.set("未知")

    def recharge(self):
        user_id = int(self.user_id_var.get())
        amount = float(self.amount_var.get())
        if amount > 0:
            old_balance = self.db_manager.get_balance(user_id)
            if old_balance is not None:
                new_balance = old_balance + amount
                self.db_manager.update_balance(user_id, new_balance)
                self.db_manager.add_transaction(user_id, amount, 'deposit')
                messagebox.showinfo("充值成功", f"充值{amount}元成功！")
                self.balance_var.set(str(new_balance))
            else:
                messagebox.showerror("错误", "用户不存在")
                self.balance_var.set("未知")
        else:
            messagebox.showerror("错误", "充值金额必须大于0！")

    def register_new_user(self):
        user_id = self.register_user_id_var.get()
        username = self.register_username_var.get()
        if self.db_manager.register_user(int(user_id), username=username):
            messagebox.showinfo("注册成功", f"用户{user_id}({username})注册成功！")
        else:
            messagebox.showerror("注册失败", f"用户{user_id}({username})注册失败，可能已存在或用户名重复。")

    def show_transaction_history(self, history, transaction_type):
        """显示交易记录"""
        self.history_text.delete(1.0, tk.END)
        for record in history:
            time_str = record[0].strftime('%Y-%m-%d %H:%M:%S')  
            amount = record[1]
            message = f"{time_str}: {transaction_type} {amount}元"
            self.history_text.insert(tk.END, message + "\n")
    
    def show_deposit_history(self):
        user_id = self.user_id_var.get()
        deposit_history = self.db_manager.get_transactions(user_id, 'deposit')
        self.show_transaction_history(deposit_history, "充值")
    
    def show_spend_history(self):
        user_id = self.user_id_var.get()
        spend_history = self.db_manager.get_transactions(user_id, 'spend')
        self.show_transaction_history(spend_history, "消费")

def main():
    db_path = 'member_management.db'
    db_manager = DatabaseManager(db_path)
    app = RechargeApp(db_manager)
    app.mainloop()

if __name__ == "__main__":
    main()
