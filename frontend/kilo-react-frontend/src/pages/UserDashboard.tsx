import React, { useState, useEffect } from 'react';
import api from '../services/api';

interface Med { id: number; name: string; dosage: string; times: string; }
interface Reminder { id: number; text: string; when: string; recurrence?: string; }
interface Habit { id: number; name: string; active: boolean; }
interface Budget { id: number; category: string; monthly_limit: number; }
interface Transaction { id: number; description: string; amount: number; category: string; date: string; transaction_type?: string; }

const UserDashboard: React.FC = () => {
  const [meds, setMeds] = useState<Med[]>([]);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [habits, setHabits] = useState<Habit[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Transactions state
  const [showTransactions, setShowTransactions] = useState(true);
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterSearch, setFilterSearch] = useState('');
  const [transactionLimit, setTransactionLimit] = useState(50);

  // Budget editing state
  const [editingBudget, setEditingBudget] = useState<number | null>(null);
  const [editValue, setEditValue] = useState('');
  const [showAddBudget, setShowAddBudget] = useState(false);
  const [newBudgetCategory, setNewBudgetCategory] = useState('');
  const [newBudgetLimit, setNewBudgetLimit] = useState('');

  useEffect(() => {
    loadData();
  }, [transactionLimit]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');

      const [medsRes, remindersRes, habitsRes, budgetsRes, txnRes] = await Promise.all([
        api.get('/meds/').catch(e => ({ data: { meds: [] } })),
        api.get('/reminder/').catch(e => ({ data: [] })),
        api.get('/habits/').catch(e => ({ data: [] })),
        api.get('/financial/budgets').catch(e => ({ data: [] })),
        api.get(`/financial/transactions?limit=${transactionLimit}`).catch(e => ({ data: [] })),
      ]);

      setMeds(medsRes.data.meds || medsRes.data || []);
      setReminders(Array.isArray(remindersRes.data) ? remindersRes.data : []);
      setHabits(Array.isArray(habitsRes.data) ? habitsRes.data : []);
      setBudgets(Array.isArray(budgetsRes.data) ? budgetsRes.data : []);
      setTransactions(Array.isArray(txnRes.data) ? txnRes.data : []);

    } catch (err: any) {
      setError(err.message || 'Failed to load data');
      console.error('Load error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Budget functions
  const startEditBudget = (budget: Budget) => {
    setEditingBudget(budget.id);
    setEditValue(budget.monthly_limit.toString());
  };

  const saveBudget = async (budgetId: number) => {
    try {
      const newLimit = parseFloat(editValue);
      if (isNaN(newLimit) || newLimit <= 0) {
        alert('Please enter a valid amount');
        return;
      }

      await api.put(`/financial/budgets/${budgetId}`, { monthly_limit: newLimit });
      setBudgets(budgets.map(b => b.id === budgetId ? { ...b, monthly_limit: newLimit } : b));
      setEditingBudget(null);
    } catch (err) {
      console.error('Error saving budget:', err);
      alert('Failed to save budget');
    }
  };

  const deleteBudget = async (budgetId: number) => {
    if (!window.confirm('Delete this budget?')) return;

    try {
      await api.delete(`/financial/budgets/${budgetId}`);
      setBudgets(budgets.filter(b => b.id !== budgetId));
    } catch (err) {
      console.error('Error deleting budget:', err);
      alert('Failed to delete budget');
    }
  };

  const addBudget = async () => {
    try {
      const limit = parseFloat(newBudgetLimit);
      if (!newBudgetCategory || isNaN(limit) || limit <= 0) {
        alert('Please enter category and valid amount');
        return;
      }

      const response = await api.post('/financial/budgets', {
        category: newBudgetCategory.toLowerCase().replace(/\s+/g, '_'),
        monthly_limit: limit
      });

      setBudgets([...budgets, response.data]);
      setShowAddBudget(false);
      setNewBudgetCategory('');
      setNewBudgetLimit('');
    } catch (err) {
      console.error('Error adding budget:', err);
      alert('Failed to add budget');
    }
  };

  // Get unique categories from transactions
  const categories = Array.from(new Set(transactions.map(t => t.category).filter(Boolean)));

  // Filter transactions
  const filteredTransactions = transactions.filter(txn => {
    const matchesCategory = filterCategory === 'all' || txn.category === filterCategory;
    const matchesSearch = filterSearch === '' ||
      txn.description.toLowerCase().includes(filterSearch.toLowerCase()) ||
      txn.category?.toLowerCase().includes(filterSearch.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-zombie-green text-2xl">Loading your data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-red-500 text-xl">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-4xl font-bold text-zombie-green mb-8">Dashboard</h1>

      {/* Medications */}
      <div className="mb-8 bg-dark-surface border border-dark-border rounded-lg p-6">
        <h2 className="text-2xl font-bold text-zombie-green mb-4">💊 Medications ({meds.length})</h2>
        {meds.length === 0 ? (
          <p className="text-dark-text-muted">No medications</p>
        ) : (
          <div className="space-y-3">
            {meds.map(med => (
              <div key={med.id} className="flex justify-between items-center border-b border-dark-border pb-2">
                <div>
                  <span className="text-zombie-green font-semibold">{med.name}</span>
                  <span className="text-dark-text ml-2">{med.dosage}</span>
                </div>
                <span className="text-dark-text-muted">{med.times}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Reminders */}
      <div className="mb-8 bg-dark-surface border border-dark-border rounded-lg p-6">
        <h2 className="text-2xl font-bold text-zombie-green mb-4">⏰ Reminders ({reminders.length})</h2>
        {reminders.length === 0 ? (
          <p className="text-dark-text-muted">No reminders</p>
        ) : (
          <div className="space-y-3">
            {reminders.slice(0, 10).map(reminder => (
              <div key={reminder.id} className="flex justify-between items-center border-b border-dark-border pb-2">
                <span className="text-zombie-green">{reminder.text}</span>
                <span className="text-dark-text-muted text-sm">{reminder.when}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Habits */}
      <div className="mb-8 bg-dark-surface border border-dark-border rounded-lg p-6">
        <h2 className="text-2xl font-bold text-zombie-green mb-4">✅ Habits ({habits.filter(h => h.active).length})</h2>
        {habits.length === 0 ? (
          <p className="text-dark-text-muted">No habits</p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {habits.filter(h => h.active).map(habit => (
              <div key={habit.id} className="bg-dark-bg border border-dark-border rounded p-3">
                <span className="text-zombie-green">{habit.name}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Budgets - Editable */}
      <div className="mb-8 bg-dark-surface border border-dark-border rounded-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-zombie-green">💰 Budgets ({budgets.length})</h2>
          <button
            onClick={() => setShowAddBudget(!showAddBudget)}
            className="bg-zombie-green text-dark-bg px-4 py-1 rounded text-sm font-bold hover:bg-green-400"
          >
            + Add Budget
          </button>
        </div>

        {/* Add Budget Form */}
        {showAddBudget && (
          <div className="mb-4 p-4 bg-dark-bg border border-zombie-green rounded">
            <div className="grid grid-cols-2 gap-4 mb-3">
              <input
                type="text"
                placeholder="Category (e.g., groceries)"
                value={newBudgetCategory}
                onChange={(e) => setNewBudgetCategory(e.target.value)}
                className="bg-dark-surface border border-dark-border rounded px-3 py-2 text-dark-text focus:outline-none focus:border-zombie-green"
              />
              <input
                type="number"
                placeholder="Monthly limit"
                value={newBudgetLimit}
                onChange={(e) => setNewBudgetLimit(e.target.value)}
                className="bg-dark-surface border border-dark-border rounded px-3 py-2 text-dark-text focus:outline-none focus:border-zombie-green"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={addBudget}
                className="bg-zombie-green text-dark-bg px-4 py-2 rounded font-bold hover:bg-green-400"
              >
                Save
              </button>
              <button
                onClick={() => {
                  setShowAddBudget(false);
                  setNewBudgetCategory('');
                  setNewBudgetLimit('');
                }}
                className="bg-dark-border text-dark-text px-4 py-2 rounded hover:bg-gray-600"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {budgets.length === 0 ? (
          <p className="text-dark-text-muted">No budgets set</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {budgets.map(budget => (
              <div key={budget.id} className="bg-dark-bg border border-dark-border rounded p-3">
                {editingBudget === budget.id ? (
                  <div className="space-y-2">
                    <div className="text-zombie-green capitalize">{budget.category.replace(/_/g, ' ')}</div>
                    <div className="flex gap-2">
                      <input
                        type="number"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        className="flex-1 bg-dark-surface border border-zombie-green rounded px-2 py-1 text-dark-text"
                        autoFocus
                      />
                      <button
                        onClick={() => saveBudget(budget.id)}
                        className="bg-zombie-green text-dark-bg px-3 py-1 rounded text-sm font-bold hover:bg-green-400"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => setEditingBudget(null)}
                        className="bg-dark-border text-dark-text px-3 py-1 rounded text-sm hover:bg-gray-600"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-between items-center">
                    <span className="text-zombie-green capitalize">{budget.category.replace(/_/g, ' ')}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-dark-text">${budget.monthly_limit.toFixed(2)}/mo</span>
                      <button
                        onClick={() => startEditBudget(budget)}
                        className="text-zombie-green hover:text-green-400 text-sm"
                      >
                        ✏️
                      </button>
                      <button
                        onClick={() => deleteBudget(budget.id)}
                        className="text-red-500 hover:text-red-400 text-sm"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Transactions - Collapsible & Filterable */}
      <div className="mb-8 bg-dark-surface border border-dark-border rounded-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-zombie-green">
            📊 Transactions ({filteredTransactions.length}/{transactions.length})
          </h2>
          <button
            onClick={() => setShowTransactions(!showTransactions)}
            className="text-zombie-green hover:text-green-400 text-2xl font-bold"
          >
            {showTransactions ? '−' : '+'}
          </button>
        </div>

        {showTransactions && (
          <>
            {/* Filters */}
            <div className="mb-4 grid grid-cols-1 md:grid-cols-3 gap-4">
              <input
                type="text"
                placeholder="Search description..."
                value={filterSearch}
                onChange={(e) => setFilterSearch(e.target.value)}
                className="bg-dark-bg border border-dark-border rounded px-4 py-2 text-dark-text focus:outline-none focus:border-zombie-green"
              />
              <select
                value={filterCategory}
                onChange={(e) => setFilterCategory(e.target.value)}
                className="bg-dark-bg border border-dark-border rounded px-4 py-2 text-dark-text focus:outline-none focus:border-zombie-green"
              >
                <option value="all">All Categories</option>
                {categories.sort().map(cat => (
                  <option key={cat} value={cat}>{cat.replace(/_/g, ' ')}</option>
                ))}
              </select>
              <select
                value={transactionLimit}
                onChange={(e) => setTransactionLimit(Number(e.target.value))}
                className="bg-dark-bg border border-dark-border rounded px-4 py-2 text-dark-text focus:outline-none focus:border-zombie-green"
              >
                <option value="50">Last 50</option>
                <option value="100">Last 100</option>
                <option value="250">Last 250</option>
                <option value="500">Last 500</option>
                <option value="1000">Last 1000</option>
              </select>
            </div>

            {(filterCategory !== 'all' || filterSearch !== '') && (
              <button
                onClick={() => {
                  setFilterCategory('all');
                  setFilterSearch('');
                }}
                className="mb-4 text-zombie-green text-sm hover:underline"
              >
                Clear filters
              </button>
            )}

            {filteredTransactions.length === 0 ? (
              <p className="text-dark-text-muted">No transactions match your filters</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {filteredTransactions.map(txn => (
                  <div key={txn.id} className="flex justify-between items-center border-b border-dark-border pb-2 hover:bg-dark-bg px-2 py-1 rounded">
                    <div className="flex-1">
                      <span className="text-zombie-green">{txn.description}</span>
                      <span className="text-dark-text-muted text-sm ml-2 capitalize">{txn.category?.replace(/_/g, ' ')}</span>
                    </div>
                    <div className="text-right">
                      <div className={`font-semibold ${txn.transaction_type === 'income' ? 'text-green-500' : 'text-dark-text'}`}>
                        {txn.transaction_type === 'income' ? '+' : ''}${txn.amount.toFixed(2)}
                      </div>
                      <div className="text-dark-text-muted text-xs">{txn.date}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      <button
        onClick={loadData}
        className="bg-zombie-green text-dark-bg px-6 py-2 rounded font-bold hover:bg-green-400"
      >
        Refresh Data
      </button>
    </div>
  );
};

export default UserDashboard;
