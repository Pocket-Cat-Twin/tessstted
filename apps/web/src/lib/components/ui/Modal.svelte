<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { fade, scale } from 'svelte/transition';
  import Button from './Button.svelte';

  export let open = false;
  export let title: string | undefined = undefined;
  export let size: 'sm' | 'md' | 'lg' | 'xl' = 'md';
  export let closable = true;
  export let persistent = false;

  const dispatch = createEventDispatcher<{
    close: void;
    confirm: void;
    cancel: void;
  }>();

  let modalElement: HTMLDivElement;

  $: modalSizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl'
  };

  function handleBackdropClick(event: MouseEvent) {
    if (!persistent && event.target === modalElement) {
      close();
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape' && closable && !persistent) {
      close();
    }
  }

  function close() {
    if (closable) {
      open = false;
      dispatch('close');
    }
  }

  function confirm() {
    dispatch('confirm');
  }

  function cancel() {
    dispatch('cancel');
    close();
  }

  onMount(() => {
    function handleEscape(event: KeyboardEvent) {
      if (open && event.key === 'Escape' && closable && !persistent) {
        close();
      }
    }

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  });
</script>

{#if open}
  <!-- Backdrop -->
  <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
  <div
    bind:this={modalElement}
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
    transition:fade={{ duration: 200 }}
    on:click={handleBackdropClick}
    on:keydown={handleKeydown}
    role="dialog"
    aria-modal="true"
    aria-labelledby={title ? 'modal-title' : undefined}
    tabindex="-1"
  >
    <!-- Modal Content -->
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
    <div
      class="bg-white rounded-xl shadow-xl w-full {modalSizeClasses[size]} max-h-screen overflow-hidden"
      transition:scale={{ duration: 200 }}
      on:click|stopPropagation
      role="document"
    >
      <!-- Header -->
      {#if title || closable}
        <div class="flex items-center justify-between p-6 border-b border-gray-200">
          {#if title}
            <h2 id="modal-title" class="text-xl font-semibold text-gray-900">
              {title}
            </h2>
          {:else}
            <div></div>
          {/if}
          
          {#if closable}
            <button
              type="button"
              class="text-gray-400 hover:text-gray-600 transition-colors p-1 rounded-md hover:bg-gray-100"
              on:click={close}
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          {/if}
        </div>
      {/if}

      <!-- Body -->
      <div class="p-6 overflow-y-auto max-h-96">
        <slot />
      </div>

      <!-- Footer -->
      <slot name="footer" {close} {confirm} {cancel}>
        <div class="flex items-center justify-end gap-3 p-6 border-t border-gray-200 bg-gray-50">
          <Button variant="ghost" on:click={cancel}>
            Отмена
          </Button>
          <Button variant="primary" on:click={confirm}>
            Подтвердить
          </Button>
        </div>
      </slot>
    </div>
  </div>
{/if}