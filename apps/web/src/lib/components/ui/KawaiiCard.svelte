<script lang="ts">
  export let className = '';
  export let variant: 'default' | 'glass' | 'elite' | 'subtle' | 'accent' = 'default';
  export let withPattern = false;
  export let href: string | undefined = undefined;

  const variants = {
    default: 'card-gothic',
    glass: 'glass-intense rounded-xl',
    elite: 'card-gothic shadow-gothic-glow',
    subtle: 'glass-subtle rounded-xl',
    accent: 'glass border-gothic-accent rounded-xl'
  };

  $: cardClasses = `
    ${variants[variant]}
    ${withPattern ? 'pattern-overlay-7' : ''}
    ${className}
  `.trim();
</script>

{#if href}
  <a {href} class="{cardClasses} block p-8 hover-lift hover-glow transition-all duration-300">
    <slot />
  </a>
{:else}
  <div class="{cardClasses} p-8">
    <slot />
  </div>
{/if}