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
  is_recurring?: boolean;
  bill_name?: string;
  due_date?: string;
  exclude_from_balance?: boolean;  // Exclude from balance calculations
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

interface IngestedDocument {
  id: number;
  filename: string;
  content_type: string;
  kind: string;
  status: string;
  error?: string;
  transaction_count: number;
  created_at: string;
  extracted_text?: string;
}

interface SpendingAnalytics {
  total_transactions: number;
  total_spent: number;
  total_income: number;
  category_breakdown: { [key: string]: number };
  top_categories: [string, number][];
  monthly_trends: [string, number][];
  top_items: [string, number][];
  insights: string[];
  average_transaction: number;
}

const Finance: React.FC = () => {
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
  const [showUploadDocument, setShowUploadDocument] = useState(false);
  const [showIngestedDocs, setShowIngestedDocs] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({});
  const [ingestedDocuments, setIngestedDocuments] = useState<IngestedDocument[]>([]);
  const [documentKind, setDocumentKind] = useState<'receipt' | 'statement' | 'auto'>('auto');
  const [serverDocUrl, setServerDocUrl] = useState('');
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [analytics, setAnalytics] = useState<SpendingAnalytics | null>(null);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  
  // Collapsible section states
  const [showBudgets, setShowBudgets] = useState(false);
  const [showBills, setShowBills] = useState(false);
  const [showTransactions, setShowTransactions] = useState(true); // Open by default
  
  // Transaction filtering and pagination
  const [filterMonth, setFilterMonth] = useState<string>(''); // Format: 'YYYY-MM'
  const [filterYear, setFilterYear] = useState<string>(''); // Format: 'YYYY'
  const [filterCategory, setFilterCategory] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [viewMode, setViewMode] = useState<'monthly' | 'yearly' | 'all'>('monthly');
  const transactionsPerPage = 50;
  
  // Debug: log budgets after declaration
  useEffect(() => {
    if (budgets) {
      // eslint-disable-next-line no-console
      console.log('DEBUG: Budgets from backend:', budgets);
    }
  }, [budgets]);
  const [showAddBudget, setShowAddBudget] = useState(false);
  const [showAddGoal, setShowAddGoal] = useState(false);
  const [showAddBill, setShowAddBill] = useState(false);
  
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
  const [billForm, setBillForm] = useState({
    bill_name: '',
    amount: '',
    category: '',
    due_date: '',
    is_recurring: true
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
    // Set default filter to current month
    const now = new Date();
    setFilterMonth(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`);
    setFilterYear(now.getFullYear().toString());
  }, []);

  // Filter and paginate transactions
  const getFilteredTransactions = () => {
    let filtered = [...transactions];

    // Apply search filter
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter(t => 
        t.description.toLowerCase().includes(search) ||
        t.category.toLowerCase().includes(search)
      );
    }

    // Apply category filter
    if (filterCategory) {
      filtered = filtered.filter(t => t.category === filterCategory);
    }

    // Apply date filter based on view mode
    if (viewMode === 'monthly' && filterMonth) {
      filtered = filtered.filter(t => {
        const txDate = new Date(t.date);
        const txMonth = `${txDate.getFullYear()}-${String(txDate.getMonth() + 1).padStart(2, '0')}`;
        return txMonth === filterMonth;
      });
    } else if (viewMode === 'yearly' && filterYear) {
      filtered = filtered.filter(t => {
        const txDate = new Date(t.date);
        return txDate.getFullYear().toString() === filterYear;
      });
    }

    // Sort by date descending (newest first)
    filtered.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

    return filtered;
  };

  const getPaginatedTransactions = () => {
    const filtered = getFilteredTransactions();
    const startIndex = (currentPage - 1) * transactionsPerPage;
    const endIndex = startIndex + transactionsPerPage;
    return filtered.slice(startIndex, endIndex);
  };

  const getFilteredSummary = () => {
    const filtered = getFilteredTransactions();
    // Exclude transactions marked as exclude_from_balance
    const includedInBalance = filtered.filter(t => !t.exclude_from_balance);
    
    const income = includedInBalance
      .filter(t => t.transaction_type === 'income')
      .reduce((sum, t) => sum + Math.abs(t.amount), 0);
    const expenses = includedInBalance
      .filter(t => t.transaction_type === 'expense')
      .reduce((sum, t) => sum + Math.abs(t.amount), 0);
    
    return {
      total_income: income,
      total_expenses: expenses,
      balance: income - expenses,
      transactions_count: filtered.length
    };
  };

  const getUniqueCategories = () => {
    const categories = new Set(transactions.map(t => t.category));
    return Array.from(categories).sort();
  };

  const getAvailableMonths = () => {
    const months = new Set(transactions.map(t => {
      const date = new Date(t.date);
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    }));
    return Array.from(months).sort().reverse(); // Newest first
  };

  const getAvailableYears = () => {
    const years = new Set(transactions.map(t => new Date(t.date).getFullYear().toString()));
    return Array.from(years).sort().reverse(); // Newest first
  };

  const filteredTransactions = getPaginatedTransactions();
  const filteredSummary = getFilteredSummary();
  const totalPages = Math.ceil(getFilteredTransactions().length / transactionsPerPage);

  // Recalculate budgets for the currently selected month
  const getFilteredBudgets = () => {
    if (viewMode !== 'monthly' || !filterMonth) {
      return budgets; // Return as-is if not in monthly view
    }

    // Recalculate spending for each budget based on selected month
    return budgets.map(budget => {
      const monthTransactions = transactions.filter(t => {
        const txDate = new Date(t.date);
        const txMonth = `${txDate.getFullYear()}-${String(txDate.getMonth() + 1).padStart(2, '0')}`;
        return txMonth === filterMonth && t.transaction_type === 'expense';
      });

      const spent = monthTransactions
        .filter(t => t.category && t.category.toLowerCase() === budget.category.toLowerCase())
        .reduce((sum, t) => sum + Math.abs(t.amount), 0);

      const percentage = budget.monthly_limit > 0 ? (spent / budget.monthly_limit) * 100 : 0;

      return {
        ...budget,
        spent,
        percentage
      };
    });
  };

  const filteredBudgets = getFilteredBudgets();

  const fetchFinancialData = async () => {
    try {
      setLoading(true);
      const [transactionsRes, summaryRes, budgetsRes, goalsRes] = await Promise.all([
        api.get('/financial/transactions'),
        api.get('/financial/summary'),
        api.get('/financial/budgets').catch(() => ({ data: [] })),
        api.get('/financial/goals').catch(() => ({ data: [] }))
      ]);

      // Backend returns arrays directly, not wrapped objects
      setTransactions(Array.isArray(transactionsRes.data) ? transactionsRes.data : (transactionsRes.data.transactions || []));
      setSummary(summaryRes.data || {
        total_income: 0,
        total_expenses: 0,
        balance: 0,
        transactions_count: 0
      });
      setBudgets(Array.isArray(budgetsRes.data) ? budgetsRes.data : (budgetsRes.data.budgets || []));
      setGoals(Array.isArray(goalsRes.data) ? goalsRes.data : (goalsRes.data.goals || []));
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

  const handleAddBill = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/financial/transaction', {
        description: billForm.bill_name,
        amount: -Math.abs(parseFloat(billForm.amount)), // Bills are expenses (negative)
        category: billForm.category,
        transaction_type: 'expense',
        date: billForm.due_date,
        is_recurring: billForm.is_recurring,
        bill_name: billForm.bill_name,
        due_date: billForm.due_date
      });
      setShowAddBill(false);
      setBillForm({
        bill_name: '',
        amount: '',
        category: '',
        due_date: '',
        is_recurring: true
      });
      fetchFinancialData();
    } catch (error) {
      console.error('Failed to add bill:', error);
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

  const handleToggleExclude = async (transaction: Transaction) => {
    try {
      await api.put(`/financial/transaction/${transaction.id}`, {
        ...transaction,
        exclude_from_balance: !transaction.exclude_from_balance
      });
      fetchFinancialData();
    } catch (error) {
      console.error('Failed to update transaction:', error);
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

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.currentTarget.files;
    if (!files) return;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const fileKey = `${file.name}-${Date.now()}`;
      setUploadProgress(prev => ({ ...prev, [fileKey]: 0 }));

      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('kind', documentKind);

        const response = await api.post('/financial/ingest/document', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent: any) => {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            setUploadProgress(prev => ({ ...prev, [fileKey]: percentCompleted }));
          }
        });

        console.log('Document uploaded successfully:', response.data);
        setUploadProgress(prev => {
          const newProgress = { ...prev };
          delete newProgress[fileKey];
          return newProgress;
        });

        fetchIngestedDocuments();
      } catch (error) {
        console.error('Failed to upload document:', error);
        setUploadProgress(prev => {
          const newProgress = { ...prev };
          delete newProgress[fileKey];
          return newProgress;
        });
      }
    }

    // Reset input safely
    if (e.currentTarget) {
      e.currentTarget.value = '';
    }
    // Refresh analytics after upload
    fetchAnalytics();
  };

  const fetchIngestedDocuments = async () => {
    try {
      setLoadingDocs(true);
      const response = await api.get('/financial/ingested-documents');
      setIngestedDocuments(response.data.documents || []);
    } catch (error) {
      console.error('Failed to fetch ingested documents:', error);
    } finally {
      setLoadingDocs(false);
    }
  };

  const handleDeleteDocument = async (id: number) => {
    try {
      await api.delete(`/financial/ingested-documents/${id}`);
      fetchIngestedDocuments();
      fetchAnalytics();
    } catch (error) {
      console.error('Failed to delete document:', error);
      alert('Failed to delete document');
    }
  };

  const handleServerDocFetch = async () => {
    if (!serverDocUrl.trim()) {
      alert('Please enter a server document URL');
      return;
    }

    try {
      setLoadingDocs(true);
      const response = await api.post('/financial/ingest/from-server', {
        url: serverDocUrl,
        kind: documentKind
      });
      console.log('Server document fetched:', response.data);
      setServerDocUrl('');
      fetchIngestedDocuments();
      fetchAnalytics();
    } catch (error) {
      console.error('Failed to fetch document from server:', error);
      alert('Failed to fetch document from server');
    } finally {
      setLoadingDocs(false);
    }
  };

  const fetchAnalytics = async () => {
    try {
      setLoadingAnalytics(true);
      const response = await api.get('/financial/spending/analytics');
      setAnalytics(response.data);
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    } finally {
      setLoadingAnalytics(false);
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
              onClick={() => navigate('/dashboard')}
              size="sm"
            >
              ← BACK
            </Button>
            <h1 className="text-xl font-bold text-zombie-green terminal-glow">💰 FINANCE</h1>
          </div>
          <div className="flex gap-2">
            <Button
              variant="primary"
              onClick={() => setShowUploadDocument(!showUploadDocument)}
              size="sm"
            >
              {showUploadDocument ? '✕' : '📄'} UPLOAD
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setShowIngestedDocs(!showIngestedDocs);
                if (!showIngestedDocs) fetchIngestedDocuments();
              }}
              size="sm"
            >
              {showIngestedDocs ? '✕' : '📋'} DOCS
            </Button>
            <Button
              variant="success"
              onClick={() => {
                setShowAnalytics(!showAnalytics);
                if (!showAnalytics) fetchAnalytics();
              }}
              size="sm"
            >
              {showAnalytics ? '✕' : '📊'} INSIGHTS
            </Button>
            <Button
              variant="primary"
              onClick={() => setShowAddTransaction(!showAddTransaction)}
              size="sm"
            >
              {showAddTransaction ? 'Cancel' : '+ Transaction'}
            </Button>
          </div>
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

        {/* Document Upload Section */}
        {showUploadDocument && (
          <Card className="mb-2 py-3 px-4">
            <h2 className="text-base font-bold text-zombie-green terminal-glow mb-3">📄 UPLOAD DOCUMENT</h2>
            
            {/* Document Type Selector */}
            <div className="mb-3 p-3 bg-zombie-dark rounded border-2 border-zombie-green">
              <p className="text-sm text-zombie-green mb-2 font-semibold">Document Type:</p>
              <div className="flex gap-2 flex-wrap">
                {(['auto', 'receipt', 'statement'] as const).map((kind) => (
                  <button
                    key={kind}
                    onClick={() => setDocumentKind(kind)}
                    className={`px-3 py-1 text-sm rounded font-semibold ${
                      documentKind === kind
                        ? 'bg-yellow-500 text-white'
                        : 'bg-zombie-dark border-2 border-zombie-green text-zombie-green hover:bg-zombie-dark/50'
                    }`}
                  >
                    {kind.charAt(0).toUpperCase() + kind.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* File Upload Area */}
            <div className="mb-3">
              <label className="block">
                <div className="border-2 border-dashed border-zombie-green rounded-lg p-6 text-center cursor-pointer hover:bg-zombie-dark/50 transition">
                  <p className="text-zombie-green font-semibold mb-2">📁 Drag & drop or click to select</p>
                  <p className="text-xs text-zombie-green/70">PDF, PNG, JPG, etc.</p>
                  <input
                    type="file"
                    multiple
                    onChange={handleFileUpload}
                    accept=".pdf,.png,.jpg,.jpeg,.gif,.doc,.docx"
                    className="hidden"
                  />
                </div>
              </label>
            </div>

            {/* Upload Progress */}
            {Object.entries(uploadProgress).length > 0 && (
              <div className="mb-3 space-y-2">
                {Object.entries(uploadProgress).map(([fileKey, progress]) => (
                  <div key={fileKey} className="space-y-1">
                    <div className="flex justify-between text-xs text-zombie-green">
                      <span>{fileKey.split('-')[0]}</span>
                      <span>{progress}%</span>
                    </div>
                    <div className="w-full bg-zombie-dark rounded-full h-2">
                      <div
                        className="h-2 rounded-full bg-yellow-500 transition-all"
                        style={{ width: `${progress}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Server Document Fetch */}
            <div className="border-t-2 border-zombie-green pt-3 mt-3">
              <p className="text-sm text-zombie-green mb-2 font-semibold">Or fetch from server:</p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={serverDocUrl}
                  onChange={(e) => setServerDocUrl(e.target.value)}
                  placeholder="Enter server document URL..."
                  className="flex-1 p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                />
                <Button
                  onClick={handleServerDocFetch}
                  variant="success"
                  size="sm"
                  disabled={loadingDocs}
                >
                  {loadingDocs ? 'Fetching...' : 'Fetch'}
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Ingested Documents List */}
        {showIngestedDocs && (
          <Card className="mb-2 py-3 px-4">
            <h2 className="text-base font-bold text-zombie-green terminal-glow mb-3">📋 INGESTED DOCUMENTS</h2>
            {loadingDocs ? (
              <p className="text-sm text-zombie-green text-center">Loading documents...</p>
            ) : ingestedDocuments.length === 0 ? (
              <p className="text-sm text-zombie-green text-center">No documents uploaded yet</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {ingestedDocuments.map((doc) => (
                  <div key={doc.id} className="p-2 bg-zombie-dark rounded border-l-4 border-yellow-500">
                    <div className="flex justify-between items-start mb-1">
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-zombie-green">{doc.filename}</p>
                        <p className="text-xs text-zombie-green/70">
                          Type: <span className="font-mono">{doc.kind}</span> | Uploaded: {formatDate(doc.created_at)}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className={`text-xs px-2 py-1 rounded font-semibold ${
                          doc.status === 'success'
                            ? 'bg-green-500/30 text-green-300'
                            : doc.status === 'error'
                            ? 'bg-red-500/30 text-red-300'
                            : 'bg-yellow-500/30 text-yellow-300'
                        }`}>
                          {doc.status}
                        </span>
                        <button
                          onClick={() => handleDeleteDocument(doc.id)}
                          className="ml-2 text-xs text-red-300 hover:text-red-500 underline"
                          title="Delete document and its transactions"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                    <p className="text-xs text-zombie-green">
                      Transactions extracted: <span className="font-bold text-green-400">{doc.transaction_count}</span>
                    </p>
                    {doc.error && (
                      <p className="text-xs text-red-400 mt-1">Error: {doc.error}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}

        {/* Spending Analytics & Insights */}
        {showAnalytics && (
          <Card className="mb-2 py-3 px-4">
            <h2 className="text-base font-bold text-zombie-green terminal-glow mb-3">📊 SPENDING INSIGHTS</h2>
            {loadingAnalytics ? (
              <p className="text-sm text-zombie-green text-center">Crunching the numbers...</p>
            ) : !analytics ? (
              <p className="text-sm text-zombie-green text-center">No analytics data available</p>
            ) : (
              <div className="space-y-4">
                {/* Key Insights */}
                {analytics.insights && analytics.insights.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold text-zombie-green mb-2">💡 Key Insights:</h3>
                    {analytics.insights.map((insight, idx) => (
                      <div key={idx} className="p-2 bg-zombie-dark rounded border-l-4 border-yellow-500">
                        <p className="text-sm text-zombie-green">{insight}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Top Categories */}
                {analytics.top_categories && analytics.top_categories.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-zombie-green mb-2">🏆 Top Spending Categories:</h3>
                    <div className="space-y-2">
                      {analytics.top_categories.map(([category, amount], idx) => (
                        <div key={idx} className="flex justify-between items-center p-2 bg-zombie-dark rounded">
                          <span className="text-sm text-zombie-green font-semibold capitalize">{category}</span>
                          <span className="text-sm text-red-400 font-bold">${amount.toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Monthly Trends */}
                {analytics.monthly_trends && analytics.monthly_trends.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-zombie-green mb-2">📈 Monthly Spending Trends:</h3>
                    <div className="space-y-1 max-h-32 overflow-y-auto">
                      {analytics.monthly_trends.map(([month, amount], idx) => (
                        <div key={idx} className="flex justify-between items-center text-xs text-zombie-green">
                          <span>{month}</span>
                          <span className="font-bold">${amount.toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Top Items */}
                {analytics.top_items && analytics.top_items.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-zombie-green mb-2">🛒 Most Purchased Items:</h3>
                    <div className="space-y-1">
                      {analytics.top_items.map(([item, count], idx) => (
                        <div key={idx} className="flex justify-between items-center text-sm text-zombie-green">
                          <span>{item}</span>
                          <span className="px-2 py-1 bg-yellow-500/30 rounded font-bold text-yellow-300">{count}x</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Refresh Analytics Button */}
                <div className="pt-2 border-t-2 border-zombie-green">
                  <Button
                    onClick={fetchAnalytics}
                    variant="primary"
                    size="sm"
                    className="w-full"
                    disabled={loadingAnalytics}
                  >
                    {loadingAnalytics ? 'Refreshing...' : '🔄 Refresh Analytics'}
                  </Button>
                </div>
              </div>
            )}
          </Card>
        )}

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
          <div 
            className="flex items-center justify-between mb-2 cursor-pointer hover:bg-zombie-dark/30 p-2 rounded"
            onClick={() => setShowBudgets(!showBudgets)}
          >
            <h2 className="text-base font-semibold text-zombie-green terminal-glow">
              {showBudgets ? '▼' : '▶'} 📊 BUDGETS
            </h2>
            <button
              className="px-3 py-1 text-sm bg-blue-500 text-white font-semibold rounded hover:bg-blue-600"
              onClick={(e) => {
                e.stopPropagation();
                setShowAddBudget(!showAddBudget);
              }}
            >
              {showAddBudget ? 'Cancel' : '+ Budget'}
            </button>
          </div>

          {showBudgets && (
            <>
              {/* Month Filter for Budgets */}
              {viewMode === 'monthly' && (
            <Card className="mb-2 p-2">
              <div className="flex items-center gap-2">
                <label className="text-xs text-zombie-green font-semibold">Viewing budget for:</label>
                <select
                  value={filterMonth}
                  onChange={(e) => setFilterMonth(e.target.value)}
                  className="flex-1 p-1 text-sm bg-zombie-dark text-zombie-green border border-zombie-green rounded"
                >
                  {getAvailableMonths().map(month => {
                    const [year, m] = month.split('-');
                    const date = new Date(parseInt(year), parseInt(m) - 1);
                    const monthName = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
                    return (
                      <option key={month} value={month}>{monthName}</option>
                    );
                  })}
                </select>
              </div>
            </Card>
          )}

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
              {(Array.isArray(filteredBudgets) ? filteredBudgets.filter(b => b && typeof b === 'object') : []).map((budget, idx) => {
                // Use normalized ratio (0-1) for budget progress, then display as percent
                let spent = 0;
                let monthly_limit = 0;
                let ratio = 0;
                if (budget && typeof budget === 'object') {
                  spent = Number(budget.spent);
                  monthly_limit = Number(budget.monthly_limit);
                  if (!Number.isFinite(spent)) spent = 0;
                  if (!Number.isFinite(monthly_limit)) monthly_limit = 0;
                  if (monthly_limit > 0) {
                    ratio = spent / monthly_limit;
                  } else {
                    ratio = 0;
                  }
                  if (!Number.isFinite(ratio) || ratio < 0) ratio = 0;
                  if (ratio > 1) ratio = 1;
                } else {
                  // If budget is not an object, log and skip rendering
                  console.error('[FINANCE] Malformed budget object at idx', idx, budget);
                  return null;
                }
                // (Debug log removed from JSX for build compatibility)
                let percentage = ratio * 100; // Convert ratio (0-1) to percentage (0-100)
                let percentageDisplay = `${percentage.toFixed(0)}%`;
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
                            percentage >= 100 ? 'text-red-400' :
                            percentage >= 80 ? 'text-yellow-400' : 'text-green-400'
                          }`}>
                            {percentageDisplay}
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
                          className={`h-2 rounded-full ${getBudgetColor(percentage)}`}
                          style={{ width: `${Math.min(percentage, 100)}%` }}
                        ></div>
                      </div>
                      {percentage >= 100 && (
                        <p className="text-xs text-red-400 font-semibold">⚠️ Over budget!</p>
                      )}
                      {percentage >= 80 && percentage < 100 && (
                        <p className="text-xs text-yellow-400 font-semibold">⚠️ Approaching limit</p>
                      )}
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
            </>
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
                let progressDisplay;
                if (Number.isFinite(progress)) {
                  progressDisplay = `${progress.toFixed(0)}%`;
                } else {
                  console.error('[FINANCE] Invalid progress for goal:', progress);
                  progressDisplay = '0%';
                }
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
                            {progressDisplay}
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

        {/* Bills Section */}
        <div className="mb-4">
          <div 
            className="flex items-center justify-between mb-2 cursor-pointer hover:bg-zombie-dark/30 p-2 rounded"
            onClick={() => setShowBills(!showBills)}
          >
            <h2 className="text-base font-semibold text-zombie-green terminal-glow">
              {showBills ? '▼' : '▶'} 💳 RECURRING BILLS
            </h2>
            <button
              className="px-3 py-1 text-sm bg-blue-500 text-white font-semibold rounded hover:bg-blue-600"
              onClick={(e) => {
                e.stopPropagation();
                setShowAddBill(!showAddBill);
              }}
            >
              {showAddBill ? 'Cancel' : '+ Bill'}
            </button>
          </div>

          {showBills && (
            <>
              {/* Add Bill Form */}
              {showAddBill && (
            <Card className="mb-2 py-3 px-4">
              <form onSubmit={handleAddBill} className="space-y-2">
                <h3 className="text-sm font-bold text-zombie-green">ADD RECURRING BILL</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <input
                    type="text"
                    required
                    value={billForm.bill_name}
                    onChange={(e) => setBillForm({ ...billForm, bill_name: e.target.value })}
                    className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                    placeholder="Bill Name (e.g., Netflix)"
                  />
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={billForm.amount}
                    onChange={(e) => setBillForm({ ...billForm, amount: e.target.value })}
                    className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                    placeholder="Amount"
                  />
                  <input
                    type="text"
                    required
                    value={billForm.category}
                    onChange={(e) => setBillForm({ ...billForm, category: e.target.value })}
                    className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                    placeholder="Category (e.g., Utilities)"
                  />
                  <input
                    type="date"
                    required
                    value={billForm.due_date}
                    onChange={(e) => setBillForm({ ...billForm, due_date: e.target.value })}
                    className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="is_recurring"
                    checked={billForm.is_recurring}
                    onChange={(e) => setBillForm({ ...billForm, is_recurring: e.target.checked })}
                    className="w-4 h-4"
                  />
                  <label htmlFor="is_recurring" className="text-sm text-zombie-green">Recurring monthly</label>
                </div>
                <div className="flex gap-2">
                  <button
                    type="submit"
                    className="flex-1 px-4 py-2 text-sm bg-purple-500 text-white font-semibold rounded hover:bg-purple-600"
                  >
                    Add Bill
                  </button>
                  <Button
                    variant="secondary"
                    onClick={() => setShowAddBill(false)}
                    size="sm"
                    className="flex-1"
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </Card>
          )}

          {/* Bills List - Show recurring bills from transactions */}
          <Card className="py-2 px-3">
            <div className="space-y-2">
              {transactions
                .filter(t => t.is_recurring && t.bill_name)
                .sort((a, b) => new Date(a.due_date || a.date).getTime() - new Date(b.due_date || b.date).getTime())
                .slice(0, 10) // Show first 10
                .map(bill => (
                  <div key={bill.id} className="flex items-center justify-between py-2 border-b border-zombie-green/30 last:border-0">
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-zombie-green">{bill.bill_name || bill.description}</p>
                      <p className="text-xs text-zombie-green/70">
                        {bill.category} • Due: {formatDate(bill.due_date || bill.date)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-red-400">{formatCurrency(Math.abs(bill.amount))}</p>
                      <p className="text-xs text-zombie-green">monthly</p>
                    </div>
                  </div>
                ))}
              {transactions.filter(t => t.is_recurring && t.bill_name).length === 0 && (
                <p className="text-center text-sm text-zombie-green py-2">
                  No recurring bills. Click "+ Bill" to add one!
                </p>
              )}
            </div>
          </Card>
            </>
          )}
        </div>

        {/* Transactions List - Spreadsheet Format */}
        <div className="mt-4">
          <div 
            className="flex items-center justify-between mb-2 cursor-pointer hover:bg-zombie-dark/30 p-2 rounded"
            onClick={() => setShowTransactions(!showTransactions)}
          >
            <h3 className="text-base font-bold text-zombie-green terminal-glow">
              {showTransactions ? '▼' : '▶'} 📊 TRANSACTION LEDGER
            </h3>
          </div>
          
          {showTransactions && (
            <>
              {/* Filter Controls */}
              <Card className="mb-3 p-3">
            <div className="space-y-3">
              {/* View Mode Selector */}
              <div>
                <label className="text-xs text-zombie-green font-semibold mb-1 block">View Mode:</label>
                <div className="flex gap-2">
                  {(['monthly', 'yearly', 'all'] as const).map((mode) => (
                    <button
                      key={mode}
                      onClick={() => {
                        setViewMode(mode);
                        setCurrentPage(1);
                      }}
                      className={`px-3 py-1 text-sm rounded font-semibold ${
                        viewMode === mode
                          ? 'bg-zombie-green text-zombie-dark'
                          : 'bg-zombie-dark border border-zombie-green text-zombie-green hover:bg-zombie-green/20'
                      }`}
                    >
                      {mode.charAt(0).toUpperCase() + mode.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Date Filters */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {viewMode === 'monthly' && (
                  <div>
                    <label className="text-xs text-zombie-green font-semibold mb-1 block">Month:</label>
                    <select
                      value={filterMonth}
                      onChange={(e) => {
                        setFilterMonth(e.target.value);
                        setCurrentPage(1);
                      }}
                      className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border border-zombie-green rounded"
                    >
                      {getAvailableMonths().map(month => {
                        const [year, m] = month.split('-');
                        const date = new Date(parseInt(year), parseInt(m) - 1);
                        const monthName = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
                        return (
                          <option key={month} value={month}>{monthName}</option>
                        );
                      })}
                    </select>
                  </div>
                )}

                {viewMode === 'yearly' && (
                  <div>
                    <label className="text-xs text-zombie-green font-semibold mb-1 block">Year:</label>
                    <select
                      value={filterYear}
                      onChange={(e) => {
                        setFilterYear(e.target.value);
                        setCurrentPage(1);
                      }}
                      className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border border-zombie-green rounded"
                    >
                      {getAvailableYears().map(year => (
                        <option key={year} value={year}>{year}</option>
                      ))}
                    </select>
                  </div>
                )}

                <div>
                  <label className="text-xs text-zombie-green font-semibold mb-1 block">Category:</label>
                  <select
                    value={filterCategory}
                    onChange={(e) => {
                      setFilterCategory(e.target.value);
                      setCurrentPage(1);
                    }}
                    className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border border-zombie-green rounded"
                  >
                    <option value="">All Categories</option>
                    {getUniqueCategories().map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Search Bar */}
              <div>
                <label className="text-xs text-zombie-green font-semibold mb-1 block">Search:</label>
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value);
                    setCurrentPage(1);
                  }}
                  placeholder="Search description or category..."
                  className="w-full p-2 text-sm bg-zombie-dark text-zombie-green border border-zombie-green rounded"
                />
              </div>

              {/* Filtered Summary */}
              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-zombie-green/30">
                <div className="text-center">
                  <p className="text-xs text-zombie-green">Filtered Income</p>
                  <p className="text-sm font-bold text-green-400">{formatCurrency(filteredSummary.total_income)}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-zombie-green">Filtered Expenses</p>
                  <p className="text-sm font-bold text-red-400">{formatCurrency(filteredSummary.total_expenses)}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-zombie-green">Filtered Balance</p>
                  <p className={`text-sm font-bold ${filteredSummary.balance >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {formatCurrency(filteredSummary.balance)}
                  </p>
                </div>
              </div>

              {/* Transaction Count */}
              <div className="text-center text-xs text-zombie-green">
                Showing {filteredTransactions.length} of {filteredSummary.transactions_count} transactions
                {viewMode !== 'all' && ` (${viewMode} view)`}
              </div>
            </div>
          </Card>
          
          {/* Transaction Table */}
        <div className="mb-2">
          <h2 className="text-base font-semibold text-zombie-green terminal-glow mb-2">💳 TRANSACTIONS</h2>
        </div>
        {loading ? (
          <div className="text-center py-4 text-zombie-green text-sm">Loading transactions...</div>
        ) : filteredTransactions.length === 0 ? (
          <Card className="py-3 px-4">
            <p className="text-center text-sm text-zombie-green">
              {transactions.length === 0 
                ? 'No transactions yet. Click "+ Transaction" to create one!'
                : 'No transactions match your filters. Try adjusting the filters above.'}
            </p>
          </Card>
        ) : (
          <>
            <Card className="mb-2 py-2 px-2 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b-2 border-zombie-green">
                    <th className="px-2 py-2 text-left text-zombie-green font-bold">Type</th>
                    <th className="px-2 py-2 text-left text-zombie-green font-bold">Description</th>
                    <th className="px-2 py-2 text-left text-zombie-green font-bold">Category</th>
                    <th className="px-2 py-2 text-left text-zombie-green font-bold">Date</th>
                    <th className="px-2 py-2 text-right text-zombie-green font-bold">Amount</th>
                    <th className="px-2 py-2 text-center text-zombie-green font-bold text-xs" title="Exclude from balance calculations">Excl</th>
                    <th className="px-2 py-2 text-center text-zombie-green font-bold">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTransactions.map((transaction, idx) => (
                  <tr 
                    key={transaction.id} 
                    className={`border-b border-zombie-green/30 hover:bg-zombie-dark/50 ${
                      idx % 2 === 0 ? 'bg-zombie-dark/20' : ''
                    }`}
                  >
                    <td className="px-2 py-2 text-center">
                      <span className="text-lg">
                        {transaction.transaction_type === 'income' ? '💵' : '💸'}
                      </span>
                    </td>
                    <td className="px-2 py-2 text-zombie-green font-semibold truncate">
                      {transaction.description}
                    </td>
                    <td className="px-2 py-2">
                      <span className="px-2 py-1 bg-zombie-dark text-zombie-green text-xs rounded capitalize">
                        {transaction.category}
                      </span>
                    </td>
                    <td className="px-2 py-2 text-zombie-green text-xs">
                      {formatDate(transaction.date)}
                    </td>
                    <td className={`px-2 py-2 text-right font-bold ${
                      transaction.transaction_type === 'income' ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {transaction.transaction_type === 'income' ? '+' : '-'}
                      {formatCurrency(Math.abs(transaction.amount))}
                    </td>
                    <td className="px-2 py-2 text-center">
                      <input
                        type="checkbox"
                        checked={transaction.exclude_from_balance || false}
                        onChange={() => handleToggleExclude(transaction)}
                        className="w-4 h-4 cursor-pointer accent-zombie-green"
                        title="Exclude from balance (transfers, reimbursements, etc.)"
                      />
                    </td>
                    <td className="px-2 py-2 text-center">
                      <button
                        onClick={() => handleDeleteTransaction(transaction.id)}
                        className="text-red-500 hover:text-red-700 font-bold text-lg hover:bg-red-500/20 px-2 py-1 rounded"
                        title="Delete transaction"
                      >
                        ×
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <Card className="mt-2 p-3">
              <div className="flex items-center justify-between">
                <button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className={`px-3 py-1 text-sm rounded font-semibold ${
                    currentPage === 1
                      ? 'bg-zombie-dark/50 text-zombie-green/50 cursor-not-allowed'
                      : 'bg-zombie-dark border border-zombie-green text-zombie-green hover:bg-zombie-green hover:text-zombie-dark'
                  }`}
                >
                  ← Previous
                </button>
                
                <div className="text-sm text-zombie-green">
                  Page {currentPage} of {totalPages}
                </div>
                
                <button
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage === totalPages}
                  className={`px-3 py-1 text-sm rounded font-semibold ${
                    currentPage === totalPages
                      ? 'bg-zombie-dark/50 text-zombie-green/50 cursor-not-allowed'
                      : 'bg-zombie-dark border border-zombie-green text-zombie-green hover:bg-zombie-green hover:text-zombie-dark'
                  }`}
                >
                  Next →
                </button>
              </div>
            </Card>
          )}
          </>
        )}
          </>
        )}
        </div>
      </div>
    </div>
  );
};

export default Finance;
