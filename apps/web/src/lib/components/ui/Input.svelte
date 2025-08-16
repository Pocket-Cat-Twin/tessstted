<script lang="ts">
  export let id: string | undefined = undefined;
  export let name: string | undefined = undefined;
  export let type: 'text' | 'email' | 'password' | 'tel' | 'url' | 'number' = 'text';
  export let value: string | number = '';
  export let placeholder = '';
  export let disabled = false;
  export let required = false;
  export let readonly = false;
  export let error: string | undefined = undefined;
  export let label: string | undefined = undefined;
  export let helperText: string | undefined = undefined;
  export let autocomplete: string | undefined = undefined;
  export let min: number | undefined = undefined;
  export let max: number | undefined = undefined;
  export let step: number | undefined = undefined;
  export let element: HTMLInputElement | undefined = undefined;

  let inputElement: HTMLInputElement;
  
  // Sync internal element with exported element
  $: if (inputElement) {
    element = inputElement;
  }

  export function focus() {
    inputElement?.focus();
  }

  // Base input styles
  const baseInputClasses = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors';
  
  $: hasError = !!error;
  $: inputClasses = [
    baseInputClasses,
    hasError && 'border-red-500 focus:ring-red-500',
    disabled && 'opacity-50 cursor-not-allowed',
    readonly && 'bg-gray-50'
  ].filter(Boolean).join(' ');

  // Label styles
  const labelClasses = 'block text-sm font-medium text-gray-700 mb-1';
  
  // Error styles
  const errorClasses = 'text-red-600 text-sm mt-1';
</script>

<div class="w-full">
  {#if label}
    <label for={id} class={labelClasses}>
      {label}
      {#if required}
        <span class="text-red-500 ml-1">*</span>
      {/if}
    </label>
  {/if}
  
  {#if type === 'text'}
    <input
      bind:this={inputElement}
      bind:value
      {id}
      {name}
      type="text"
      {placeholder}
      {disabled}
      {required}
      {readonly}
      {autocomplete}
      class={inputClasses}
      on:input
      on:change
      on:focus
      on:blur
      on:keydown
    />
  {:else if type === 'email'}
    <input
      bind:this={inputElement}
      bind:value
      {id}
      {name}
      type="email"
      {placeholder}
      {disabled}
      {required}
      {readonly}
      {autocomplete}
      class={inputClasses}
      on:input
      on:change
      on:focus
      on:blur
      on:keydown
    />
  {:else if type === 'password'}
    <input
      bind:this={inputElement}
      bind:value
      {id}
      {name}
      type="password"
      {placeholder}
      {disabled}
      {required}
      {readonly}
      {autocomplete}
      class={inputClasses}
      on:input
      on:change
      on:focus
      on:blur
      on:keydown
    />
  {:else if type === 'tel'}
    <input
      bind:this={inputElement}
      bind:value
      {id}
      {name}
      type="tel"
      {placeholder}
      {disabled}
      {required}
      {readonly}
      {autocomplete}
      class={inputClasses}
      on:input
      on:change
      on:focus
      on:blur
      on:keydown
    />
  {:else if type === 'url'}
    <input
      bind:this={inputElement}
      bind:value
      {id}
      {name}
      type="url"
      {placeholder}
      {disabled}
      {required}
      {readonly}
      {autocomplete}
      class={inputClasses}
      on:input
      on:change
      on:focus
      on:blur
      on:keydown
    />
  {:else if type === 'number'}
    <input
      bind:this={inputElement}
      bind:value
      {id}
      {name}
      type="number"
      {placeholder}
      {disabled}
      {required}
      {readonly}
      {autocomplete}
      {min}
      {max}
      {step}
      class={inputClasses}
      on:input
      on:change
      on:focus
      on:blur
      on:keydown
    />
  {/if}
  
  {#if error}
    <p class={errorClasses}>{error}</p>
  {:else if helperText}
    <p class="text-gray-500 text-sm mt-1">{helperText}</p>
  {/if}
</div>

