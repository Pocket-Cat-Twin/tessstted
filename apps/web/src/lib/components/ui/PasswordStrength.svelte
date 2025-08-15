<script lang="ts">
  import { getPasswordStrength } from '$lib/utils/validation';
  
  export let password: string = '';
  export let show: boolean = true;
  
  $: strength = getPasswordStrength(password);
  $: showStrength = show && password.length > 0;
  
  function getStrengthBarWidth(score: number): string {
    if (score <= 2) return 'w-1/3';
    if (score <= 4) return 'w-2/3';
    return 'w-full';
  }
  
  function getStrengthBarColor(score: number): string {
    if (score <= 2) return 'bg-red-500';
    if (score <= 4) return 'bg-yellow-500';
    return 'bg-green-500';
  }
</script>

{#if showStrength}
  <div class="mt-2 space-y-2">
    <!-- Strength bar -->
    <div class="w-full bg-gray-200 rounded-full h-2">
      <div 
        class="h-2 rounded-full transition-all duration-300 {getStrengthBarColor(strength.score)} {getStrengthBarWidth(strength.score)}"
      ></div>
    </div>
    
    <!-- Strength label -->
    <div class="flex justify-between items-center text-sm">
      <span class="text-gray-600">Надежность пароля:</span>
      <span class="{strength.color} font-medium">{strength.label}</span>
    </div>
    
    <!-- Password requirements -->
    <div class="text-xs text-gray-500 space-y-1">
      <div class="flex items-center space-x-2">
        <div class="w-2 h-2 rounded-full {password.length >= 8 ? 'bg-green-500' : 'bg-gray-300'}"></div>
        <span>Минимум 8 символов</span>
      </div>
      <div class="flex items-center space-x-2">
        <div class="w-2 h-2 rounded-full {/[a-zA-Zа-яА-Я]/.test(password) ? 'bg-green-500' : 'bg-gray-300'}"></div>
        <span>Содержит буквы</span>
      </div>
      <div class="flex items-center space-x-2">
        <div class="w-2 h-2 rounded-full {/\d/.test(password) ? 'bg-green-500' : 'bg-gray-300'}"></div>
        <span>Содержит цифры</span>
      </div>
      <div class="flex items-center space-x-2">
        <div class="w-2 h-2 rounded-full {/[^a-zA-Z0-9а-яА-Я]/.test(password) ? 'bg-green-500' : 'bg-gray-300'}"></div>
        <span>Содержит спецсимволы (рекомендуется)</span>
      </div>
    </div>
  </div>
{/if}