<script lang="ts">
  export let position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center' = 'top-right';
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let opacity = 0.4;

  const positions = {
    'top-left': 'top-4 left-4',
    'top-right': 'top-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'bottom-right': 'bottom-4 right-4',
    'center': 'top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2'
  };

  const sizes = {
    sm: 'text-lg',
    md: 'text-2xl',
    lg: 'text-4xl'
  };

  const flowers = [''];
  const randomFlower = flowers[Math.floor(Math.random() * flowers.length)];
</script>

<div 
  class="absolute {positions[position]} {sizes[size]} pointer-events-none select-none"
  style="opacity: {opacity}; color: #efb0b6;"
>
  {randomFlower}
</div>