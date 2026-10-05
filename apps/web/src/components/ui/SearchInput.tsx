import { forwardRef, type InputHTMLAttributes } from 'react'
import { SearchIcon } from '@/assets/icons/CommonIcons'
import { cn } from '@/utils/cn'

export interface SearchInputProps extends InputHTMLAttributes<HTMLInputElement> {
  wrapperClassName?: string
}

export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(
  ({ className, wrapperClassName, ...props }, ref) => {
    return (
      <div className={cn('relative', wrapperClassName)}>
        <SearchIcon className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-text-muted" />
        <input
          ref={ref}
          type="search"
          className={cn(
            'w-full rounded-lg border border-sidebar-border bg-elevated py-2 pr-3 pl-9 text-sm shadow-sm',
            'placeholder:text-text-muted',
            'focus:border-homemind focus:outline-none focus:ring-2 focus:ring-homemind/20',
            className,
          )}
          {...props}
        />
      </div>
    )
  },
)

SearchInput.displayName = 'SearchInput'
