<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { fly } from 'svelte/transition';

  export let type: 'success' | 'error' | 'warning' | 'info' = 'info';
  export let message: string;
  export let duration = 5000;
  export let dismissible = true;
  export let show = true;

  const dispatch = createEventDispatcher<{
    dismiss: void;
  }>();

  let timeout: any;

  $: iconClasses = {
    success: 'text-green-500',
    error: 'text-red-500',
    warning: 'text-yellow-500',
    info: 'text-blue-500'
  };

  $: bgClasses = {
    success: 'bg-green-50 border-green-200',
    error: 'bg-red-50 border-red-200',
    warning: 'bg-yellow-50 border-yellow-200',
    info: 'bg-blue-50 border-blue-200'
  };

  $: textClasses = {
    success: 'text-green-800',
    error: 'text-red-800',
    warning: 'text-yellow-800',
    info: 'text-blue-800'
  };

  function dismiss() {
    show = false;
    dispatch('dismiss');
  }

  function getIcon(toastType: string) {
    switch (toastType) {
      case 'success':
        return 'M5 13l4 4L19 7';
      case 'error':
        return 'M6 18L18 6M6 6l12 12';
      case 'warning':
        return 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z';
      case 'info':
        return 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
      default:
        return '';
    }
  }

  onMount(() => {
    if (duration > 0) {
      timeout = setTimeout(() => {
        dismiss();
      }, duration);
    }

    return () => {
      if (timeout) {
        clearTimeout(timeout);
      }
    };
  });
</script>

{#if show}
  <div
    class="flex items-start p-4 rounded-lg border {bgClasses[type]} shadow-sm"
    transition:fly={{ y: -20, duration: 300 }}
    role="alert"
  >
    <!-- Icon -->
    <div class="flex-shrink-0">
      <svg 
        class="w-5 h-5 {iconClasses[type]}"
        fill="none" 
        stroke="currentColor" 
        viewBox="0 0 24 24"
      >
        {#if type === 'success'}
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getIcon(type)} />
        {:else if type === 'error'}
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getIcon(type)} />
        {:else if type === 'warning'}
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getIcon(type)} />
        {:else if type === 'info'}
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getIcon(type)} />
        {/if}
      </svg>
    </div>

    <!-- Message -->
    <div class="ml-3 flex-1">
      <p class="text-sm font-medium {textClasses[type]}">
        {message}
      </p>
      <slot />
    </div>

    <!-- Dismiss Button -->
    {#if dismissible}
      <div class="ml-4 flex-shrink-0">
        <button
          type="button"
          class="inline-flex text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-md p-1"
          on:click={dismiss}
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    {/if}
  </div>
{/if}