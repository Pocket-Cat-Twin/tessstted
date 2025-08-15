<script lang="ts">
  import { cn } from '$lib/utils/cn';

  export let className = '';
  export let variant: 'default' | 'bordered' | 'shadow' = 'default';
  export let padding: 'none' | 'sm' | 'md' | 'lg' = 'md';
  export let rounded: 'none' | 'sm' | 'md' | 'lg' | 'xl' = 'lg';

  const variants = {
    default: 'bg-white/80 border border-gray-200',
    bordered: 'bg-white/80 border-2 border-gray-200',
    shadow: 'bg-white/80 shadow-md border border-gray-100',
  };

  const paddings = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };

  const roundings = {
    none: '',
    sm: 'rounded-sm',
    md: 'rounded-md',
    lg: 'rounded-lg',
    xl: 'rounded-xl',
  };

  $: classes = cn(
    'transition-all duration-200',
    variants[variant],
    paddings[padding],
    roundings[rounded],
    className
  );
</script>

<div class={classes}>
  <slot />
</div>