import React from 'react';

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  className?: string;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  disabled = false,
  className = '',
}) => {
  const baseStyles = 'font-header rounded-lg font-semibold transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed';

  const variants = {
    primary:   'bg-zombie-green text-dark-bg hover:bg-terminal-green border-2 border-zombie-green shadow-md shadow-zombie-green/30',
    secondary: 'bg-dark-card text-zombie-green hover:bg-dark-border border-2 border-zombie-green/60 hover:border-zombie-green',
    success:   'bg-green-600 text-white hover:bg-green-700 border-2 border-green-600',
    danger:    'bg-red-600 text-white hover:bg-red-700 border-2 border-red-600',
    outline:   'bg-transparent text-zombie-green border-2 border-zombie-green hover:bg-dark-card',
  };

  const sizes = {
    sm: 'px-4 py-2 text-xs min-h-[40px]',
    md: 'px-6 py-3 text-sm min-h-[48px]',
    lg: 'px-8 py-4 text-base min-h-[56px]',
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
};
