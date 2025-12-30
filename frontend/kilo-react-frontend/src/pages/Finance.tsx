import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/shared/Button';
import { Card } from '../components/shared/Card';
import api from '../services/api';

interface Transaction {
  id: number;
  description: string;
  amount: number;
  category: string;
  transaction_type: 'income' | 'expense';
  date: string;
  created_at: string;
}

interface FinancialSummary {
  total_income: number;
  total_expenses: number;
  balance: number;
  transactions_count: number;
}

interface Budget {
  id: number;
  category: string;
  monthly_limit: number;
  spent: number;
  percentage: number;
}

interface FinancialGoal {
  id: number;
  name: string;
  target_amount: number;
  current_amount: number;
  deadline: string;
  category: string;
}

const Finance: React.FC = () => {
    // Debug: log budgets before rendering
    useEffect(() => {
      if (budgets) {
        // eslint-disable-next-line no-console
        console.log('DEBUG: Budgets from backend:', budgets);
      }
    }, [budgets]);
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [goals, setGoals] = useState<FinancialGoal[]>([]);
  const [summary, setSummary] = useState<FinancialSummary>({
    total_income: 0,
    total_expenses: 0,
    balance: 0,
    transactions_count: 0
  });
  const [loading, setLoading] = useState(true);
  const [showAddTransaction, setShowAddTransaction] = useState(false);
  const [showAddBudget, setShowAddBudget] = useState(false);
  const [showAddGoal, setShowAddGoal] = useState(false);
  const [transactionForm, setTransactionForm] = useState({
    description: '',
    amount: '',
    category: '',
    transaction_type: 'expense' as 'income' | 'expense',
    date: new Date().toISOString().split('T')[0]
  });
  const [budgetForm, setBudgetForm] = useState({
    category: '',
    monthly_limit: ''
  });
  const [goalForm, setGoalForm] = useState({
    name: '',
    target_amount: '',
    current_amount: '0',
    deadline: '',
    category: 'savings'
  });

  useEffect(() => {
    fetchFinancialData();
  }, []);

  const fetchFinancialData = async () => {
    try {
      setLoading(true);
      const [transactionsRes, summaryRes, budgetsRes, goalsRes] = await Promise.all([
        api.get('/financial/transactions'),
        api.get('/financial/summary'),
        api.get('/financial/budgets').catch(() => ({ data: { budgets: [] } })),
        api.get('/financial/goals').catch(() => ({ data: { goals: [] } }))
      ]);

      setTransactions(transactionsRes.data.transactions || []);
      setSummary(summaryRes.data || {
        total_income: 0,
        total_expenses: 0,
        balance: 0,
        transactions_count: 0
      });
      setBudgets(budgetsRes.data.budgets || []);
      setGoals(goalsRes.data.goals || []);
    } catch (error) {
      console.error('Failed to fetch financial data:', error);
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleAddTransaction = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/financial/transaction', {
        ...transactionForm,
        amount: parseFloat(transactionForm.amount)
      });
      setShowAddTransaction(false);
      setTransactionForm({
        description: '',
        amount: '',
        category: '',
        transaction_type: 'expense',
        date: new Date().toISOString().split('T')[0]
      });
      fetchFinancialData();
    } catch (error) {
      console.error('Failed to add transaction:', error);
    }
  };

  const handleAddBudget = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/financial/budget', {
        category: budgetForm.category,
        monthly_limit: parseFloat(budgetForm.monthly_limit)
      });
      setShowAddBudget(false);
      setBudgetForm({ category: '', monthly_limit: '' });
      fetchFinancialData();
    } catch (error) {
      console.error('Failed to add budget:', error);
    }
  };

  const handleAddGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/financial/goal', {
        name: goalForm.name,
        target_amount: parseFloat(goalForm.target_amount),
        current_amount: parseFloat(goalForm.current_amount),
        deadline: goalForm.deadline,
        category: goalForm.category
      });
      setShowAddGoal(false);
      setGoalForm({
        name: '',
        target_amount: '',
        current_amount: '0',
        deadline: '',
        category: 'savings'
      });
      fetchFinancialData();
    } catch (error) {
      console.error('Failed to add goal:', error);
    }
  };

  const handleDeleteTransaction = async (id: number) => {
    try {
      await api.delete(`/financial/transaction/${id}`);
      fetchFinancialData();
    } catch (error) {
      console.error('Failed to delete transaction:', error);
    }
  };

  const handleDeleteBudget = async (id: number) => {
    try {
      await api.delete(`/financial/budget/${id}`);
      fetchFinancialData();
    } catch (error) {
      console.error('Failed to delete budget:', error);
    }
  };

  const handleDeleteGoal = async (id: number) => {
    try {
      await api.delete(`/financial/goal/${id}`);
      fetchFinancialData();
    } catch (error) {
      console.error('Failed to delete goal:', error);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const formatDate = (date: string) => {
    try {
      return new Date(date).toLocaleDateString();
    } catch {
      return date;
    }
  };

  const getBudgetColor = (percentage: number) => {
    if (percentage >= 100) return 'bg-red-500';
    if (percentage >= 80) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const calculateGoalProgress = (current: number, target: number) => {
    return Math.min((current / target) * 100, 100);
  };

  const estimateCompletionDate = (current: number, target: number, monthlyRate: number) => {
    if (monthlyRate <= 0) return 'N/A';
    const remaining = target - current;
    const monthsNeeded = Math.ceil(remaining / monthlyRate);
    const completionDate = new Date();
    completionDate.setMonth(completionDate.getMonth() + monthsNeeded);
    return completionDate.toLocaleDateString();
  };

  return (
    <div className="min-h-screen zombie-gradient p-2">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={() => navigate('/tablet')}
              size="sm"
            >
              ← BACK
            </Button>
            <h1 className="text-xl font-bold text-zombie-green terminal-glow">💰 FINANCE</h1>
          </div>
          <Button
            variant="primary"
            onClick={() => setShowAddTransaction(!showAddTransaction)}
            size="sm"
          >
            {showAddTransaction ? 'Cancel' : '+ Transaction'}
          </Button>
        </div>

        {/* Financial Summary */}
        <div className="grid gap-2 grid-cols-3 mb-2">
          <Card className="py-2 px-3">
            <div className="text-center">
              <p className="text-xs text-zombie-green mb-1">Income</p>
              <p className="text-lg font-bold text-green-400">
                {formatCurrency(summary.total_income)}
              </p>
            </div>
          </Card>

          <Card className="py-2 px-3">
            <div className="text-center">
              <p className="text-xs text-zombie-green mb-1">Expenses</p>
              <p className="text-lg font-bold text-red-400">
                {formatCurrency(summary.total_expenses)}
              </p>
            </div>
          </Card>

          <Card className="py-2 px-3">
            <div className="text-center">
              <p className="text-xs text-zombie-green mb-1">Balance</p>
              <p className={`text-lg font-bold ${summary.balance >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {formatCurrency(summary.balance)}
              </p>
            </div>
          </Card>
        </div>

        {/* Add Transaction Form */}
        {showAddTransaction && (
          <Card className="mb-2 py-3 px-4">
            <form onSubmit={handleAddTransaction} className="space-y-3">
              <h2 className="text-base font-bold text-zombie-green terminal-glow mb-2">ADD TRANSACTION</h2>

              <div className="space-y-2">
                <input
                  type="text"
                  required
                  value={transactionForm.description}
                  onChange={(e) => setTransactionForm({ ...transactionForm, description: e.target.value })}
                  className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                  placeholder="Description"
                />

                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={transactionForm.amount}
                    onChange={(e) => setTransactionForm({ ...transactionForm, amount: e.target.value })}
                    className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                    placeholder="Amount"
                  />

                  <input
                    type="text"
                    required
                    value={transactionForm.category}
                    onChange={(e) => setTransactionForm({ ...transactionForm, category: e.target.value })}
                    className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                    placeholder="Category"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <select
                    value={transactionForm.transaction_type}
                    onChange={(e) => setTransactionForm({ ...transactionForm, transaction_type: e.target.value as 'income' | 'expense' })}
                    className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                  >
                    <option value="expense">Expense</option>
                    <option value="income">Income</option>
                  </select>

                  <input
                    type="date"
                    required
                    value={transactionForm.date}
                    onChange={(e) => setTransactionForm({ ...transactionForm, date: e.target.value })}
                    className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 text-sm bg-yellow-500 text-white font-semibold rounded hover:bg-yellow-600"
                >
                  Add
                </button>
                <Button
                  variant="secondary"
                  onClick={() => setShowAddTransaction(false)}
                  size="sm"
                  className="flex-1"
                >
                  Cancel
                </Button>
              </div>
            </form>
          </Card>
        )}

        {/* Budget Tracking Section */}
        <div className="mb-2">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-base font-semibold text-zombie-green terminal-glow">📊 BUDGETS</h2>
            <Button
              variant="primary"
              onClick={() => setShowAddBudget(!showAddBudget)}
              size="sm"
            >
              {showAddBudget ? 'Cancel' : '+ Budget'}
            </Button>
          </div>

          {/* Add Budget Form */}
          {showAddBudget && (
            <Card className="mb-2 py-3 px-4">
              <form onSubmit={handleAddBudget} className="space-y-2">
                <h3 className="text-sm font-bold text-zombie-green">ADD MONTHLY BUDGET</h3>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    required
                    value={budgetForm.category}
                    onChange={(e) => setBudgetForm({ ...budgetForm, category: e.target.value })}
                    className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                    placeholder="Category (e.g., Groceries)"
                  />
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={budgetForm.monthly_limit}
                    onChange={(e) => setBudgetForm({ ...budgetForm, monthly_limit: e.target.value })}
                    className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                    placeholder="Monthly Limit"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="submit"
                    className="flex-1 px-4 py-2 text-sm bg-blue-500 text-white font-semibold rounded hover:bg-blue-600"
                  >
                    Add Budget
                  </button>
                  <Button
                    variant="secondary"
                    onClick={() => setShowAddBudget(false)}
                    size="sm"
                    className="flex-1"
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </Card>
          )}

          {/* Budget List */}
          {budgets.length === 0 ? (
            <Card className="py-3 px-4 mb-2">
              <p className="text-center text-sm text-zombie-green">
                No budgets set. Click "+ Budget" to create one!
              </p>
            </Card>
          ) : (
            <div className="space-y-2 mb-2">
              {(Array.isArray(budgets) ? budgets.filter(b => b && typeof b === 'object') : []).map((budget, idx) => {
                // Defensive fallback for undefined/null/malformed values
                let spent = 0;
                let monthly_limit = 0;
                let percentage = 0;
                if (budget && typeof budget === 'object') {
                  spent = Number(budget.spent);
                  monthly_limit = Number(budget.monthly_limit);
                  if (!Number.isFinite(spent)) spent = 0;
                  if (!Number.isFinite(monthly_limit)) monthly_limit = 0;
                  if ('percentage' in budget && Number.isFinite(budget.percentage)) {
                    percentage = budget.percentage;
                  } else if (monthly_limit > 0) {
                    percentage = (spent / monthly_limit) * 100;
                  } else {
                    percentage = 0;
                  }
                }
                // Log all values for debugging
                // eslint-disable-next-line no-console
                console.log(`[BUDGET DEBUG] idx=${idx} id=${budget.id} category=${budget.category} spent=${spent} monthly_limit=${monthly_limit} percentage=${percentage}`);
                return (
                  <Card key={budget.id || Math.random()} className="py-2 px-3">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <h3 className="font-bold text-zombie-green text-sm">{budget.category || 'Unknown'}</h3>
                          <p className="text-xs text-zombie-green">
                            {formatCurrency(spent)} / {formatCurrency(monthly_limit)}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-sm font-bold ${
                            Number.isFinite(percentage) && percentage >= 100 ? 'text-red-400' :
                            Number.isFinite(percentage) && percentage >= 80 ? 'text-yellow-400' : 'text-green-400'
                          }`}>
                            (Number.isFinite(percentage) && typeof percentage === 'number')
                              ? percentage.toFixed(0)
                              : (() => { console.error('[FINANCE] Invalid percentage for budget:', percentage); return '0'; })()
                            }%
                          </span>
                          <button
                            onClick={() => handleDeleteBudget(budget.id)}
                            className="text-red-500 hover:text-red-700 text-lg"
                          >
                            ×
                          </button>
                        </div>
                      </div>
                      <div className="w-full bg-zombie-dark rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${getBudgetColor(Number.isFinite(percentage) ? percentage : 0)}`}
                          style={{ width: `${Math.min(Number.isFinite(percentage) ? percentage : 0, 100)}%` }}
                        ></div>
                      </div>
                      {Number.isFinite(percentage) && percentage >= 100 && (
                        <p className="text-xs text-red-400 font-semibold">⚠️ Over budget!</p>
                      )}
                      {Number.isFinite(percentage) && percentage >= 80 && percentage < 100 && (
                        <p className="text-xs text-yellow-400 font-semibold">⚠️ Approaching limit</p>
                      )}
                    </div>
                  </Card>
                );
              })}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Financial Goals Section */}
        <div className="mb-2">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-base font-semibold text-zombie-green terminal-glow">🎯 FINANCIAL GOALS</h2>
            <Button
              variant="primary"
              onClick={() => setShowAddGoal(!showAddGoal)}
              size="sm"
            >
              {showAddGoal ? 'Cancel' : '+ Goal'}
            </Button>
          </div>

          {/* Add Goal Form */}
          {showAddGoal && (
            <Card className="mb-2 py-3 px-4">
              <form onSubmit={handleAddGoal} className="space-y-2">
                <h3 className="text-sm font-bold text-zombie-green">ADD SAVINGS GOAL</h3>
                <input
                  type="text"
                  required
                  value={goalForm.name}
                  onChange={(e) => setGoalForm({ ...goalForm, name: e.target.value })}
                  className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                  placeholder="Goal Name (e.g., Emergency Fund)"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={goalForm.target_amount}
                    onChange={(e) => setGoalForm({ ...goalForm, target_amount: e.target.value })}
                    className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                    placeholder="Target Amount"
                  />
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={goalForm.current_amount}
                    onChange={(e) => setGoalForm({ ...goalForm, current_amount: e.target.value })}
                    className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                    placeholder="Current Amount"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="date"
                    required
                    value={goalForm.deadline}
                    onChange={(e) => setGoalForm({ ...goalForm, deadline: e.target.value })}
                    className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                  />
                  <select
                    value={goalForm.category}
                    onChange={(e) => setGoalForm({ ...goalForm, category: e.target.value })}
                    className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                  >
                    <option value="savings">Savings</option>
                    <option value="emergency">Emergency Fund</option>
                    <option value="equipment">Equipment</option>
                    <option value="healthcare">Healthcare</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div className="flex gap-2">
                  <button
                    type="submit"
                    className="flex-1 px-4 py-2 text-sm bg-purple-500 text-white font-semibold rounded hover:bg-purple-600"
                  >
                    Add Goal
                  </button>
                  <Button
                    variant="secondary"
                    onClick={() => setShowAddGoal(false)}
                    size="sm"
                    className="flex-1"
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </Card>
          )}

          {/* Goals List */}
          {goals.length === 0 ? (
            <Card className="py-3 px-4 mb-2">
              <p className="text-center text-sm text-zombie-green">
                No goals set. Click "+ Goal" to create one!
              </p>
            </Card>
          ) : (
            <div className="space-y-2 mb-2">
              {goals.map((goal) => {
                const safeCurrent = Number.isFinite(goal.current_amount) ? goal.current_amount : 0;
                const safeTarget = Number.isFinite(goal.target_amount) ? goal.target_amount : 0;
                const progress = calculateGoalProgress(safeCurrent, safeTarget);
                // eslint-disable-next-line no-console
                console.log(`[GOAL DEBUG] id=${goal.id} name=${goal.name} current_amount=${safeCurrent} target_amount=${safeTarget} progress=${progress}`);
                const monthlyRate = 100; // Mock monthly savings rate
                return (
                  <Card key={goal.id} className="py-2 px-3">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <h3 className="font-bold text-zombie-green text-sm">{goal.name}</h3>
                          <p className="text-xs text-zombie-green">
                            {formatCurrency(safeCurrent)} / {formatCurrency(safeTarget)}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-blue-400">
                            {(Number.isFinite(progress) && typeof progress === 'number')
                              ? progress.toFixed(0)
                              : (() => { console.error('[FINANCE] Invalid progress for goal:', progress); return '0'; })()
                            }%
                          </span>
                          <button
                            onClick={() => handleDeleteGoal(goal.id)}
                            className="text-red-500 hover:text-red-700 text-lg"
                          >
                            ×
                          </button>
                        </div>
                      </div>
                      <div className="w-full bg-zombie-dark rounded-full h-2">
                        <div
                          className="h-2 rounded-full bg-blue-500"
                          style={{ width: `${progress}%` }}
                        ></div>
                      </div>
                      <div className="flex justify-between text-xs text-zombie-green">
                        <span>📅 Deadline: {formatDate(goal.deadline)}</span>
                        <span>📈 Est. completion: {estimateCompletionDate(goal.current_amount, goal.target_amount, monthlyRate)}</span>
                      </div>
                      {progress >= 100 && (
                        <p className="text-xs text-green-400 font-semibold">🎉 Goal achieved!</p>
                      )}
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>

        {/* Transactions List */}
        <div className="mb-2">
          <h2 className="text-base font-semibold text-zombie-green terminal-glow mb-2">💳 RECENT TRANSACTIONS</h2>
        </div>
        {loading ? (
          <div className="text-center py-4 text-zombie-green text-sm">Loading transactions...</div>
        ) : transactions.length === 0 ? (
          <Card className="py-3 px-4">
            <p className="text-center text-sm text-zombie-green">
              No transactions yet. Click "+ Transaction" to create one!
            </p>
          </Card>
        ) : (
          <div className="space-y-2">
            {transactions.map((transaction) => (
              <Card key={transaction.id} className="py-2 px-3">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">
                        {transaction.transaction_type === 'income' ? '💵' : '💸'}
                      </span>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-bold text-zombie-green text-sm">{transaction.description}</h3>
                        <div className="flex items-center gap-2 text-xs text-zombie-green">
                          <span className="px-1 py-0.5 bg-zombie-dark rounded">
                            {transaction.category}
                          </span>
                          <span>{formatDate(transaction.date)}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-bold ${
                      transaction.transaction_type === 'income' ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {transaction.transaction_type === 'income' ? '+' : '-'}
                      {formatCurrency(Math.abs(transaction.amount))}
                    </span>
                    <button
                      onClick={() => handleDeleteTransaction(transaction.id)}
                      className="text-red-500 hover:text-red-700 text-lg"
                      title="Delete transaction"
                    >
                      ×
                    </button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Finance;
