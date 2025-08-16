<script lang="ts">
  import { onMount } from 'svelte';
  import Button from '$components/ui/Button.svelte';
  import GothicButton from '$components/ui/KawaiiButton.svelte';
  import GothicCard from '$components/ui/KawaiiCard.svelte';
  import { configStore } from '$stores/config';
  import { fade, fly } from 'svelte/transition';

  $: config = $configStore.config;
  $: currentKurs = $configStore.kurs;

  let mounted = false;

  onMount(() => {
    mounted = true;
  });
</script>

<svelte:head>
  <title>YuYu Lolita Shopping - Professional Ordering from China</title>
  <meta name="description" content="YuYu Lolita Shopping - premium ordering service from China to Russia. Professional, reliable, efficient." />
</svelte:head>

<!-- Hero Section -->
<section class="relative overflow-hidden section-gothic-primary pattern-overlay-7">
  
  <div class="relative container-custom section-py">
    <div class="text-center max-w-4xl mx-auto">
      <!-- Main heading -->
      {#if mounted}
        <h1 
          class="text-4xl md:text-6xl font-bold text-elegant mb-8 hero-gothic text-shadow-gothic"
          in:fly={{ y: 30, duration: 600, delay: 100 }}
        >
          <span class="text-gothic block mb-4">Orders from China</span>
          <span class="text-gradient block">Made Simple</span>
        </h1>
      {:else}
        <h1 class="text-4xl md:text-6xl font-bold text-elegant mb-8 hero-gothic text-shadow-gothic">
          <span class="text-gothic block mb-4">Orders from China</span>
          <span class="text-gradient block">Made Simple</span>
        </h1>
      {/if}

      <!-- Subtitle -->
      {#if mounted}
        <p 
          class="text-xl text-gothic-secondary mb-12 max-w-2xl mx-auto leading-relaxed"
          in:fly={{ y: 30, duration: 600, delay: 200 }}
        >
          Professional assistance in ordering products from Chinese platforms. 
          Transparent pricing, fast delivery, complete support.
        </p>
      {:else}
        <p class="text-xl text-gothic-secondary mb-12 max-w-2xl mx-auto leading-relaxed">
          Professional assistance in ordering products from Chinese platforms. 
          Transparent pricing, fast delivery, complete support.
        </p>
      {/if}

      <!-- Currency rate -->
      {#if mounted}
        <div 
          class="inline-flex items-center glass rounded-lg px-6 py-4 mb-12 hover-glow"
          in:fly={{ y: 30, duration: 600, delay: 300 }}
        >
          <div class="w-3 h-3 bg-gothic-accent rounded-full mr-4 animate-pulse"></div>
          <span class="text-gothic-white font-medium">
            Current Rate: <span class="text-gothic-accent font-bold">{currentKurs} ₽/¥</span>
          </span>
        </div>
      {:else}
        <div class="inline-flex items-center glass rounded-lg px-6 py-4 mb-12 hover-glow">
          <div class="w-3 h-3 bg-gothic-accent rounded-full mr-4 animate-pulse"></div>
          <span class="text-gothic-white font-medium">
            Current Rate: <span class="text-gothic-accent font-bold">{currentKurs} ₽/¥</span>
          </span>
        </div>
      {/if}

      <!-- CTA Buttons -->
      {#if mounted}
        <div 
          class="flex flex-col sm:flex-row gap-6 justify-center items-center"
          in:fly={{ y: 30, duration: 600, delay: 400 }}
        >
          <a href="/create" class="btn-gothic hover-lift">
            Create Order
          </a>
          
          <a href="/track" class="btn-white hover-lift">
            Track Order
          </a>
        </div>
      {:else}
        <div class="flex flex-col sm:flex-row gap-6 justify-center items-center">
          <a href="/create" class="btn-gothic hover-lift">
            Create Order
          </a>
          
          <a href="/track" class="btn-white hover-lift">
            Track Order
          </a>
        </div>
      {/if}
    </div>
  </div>
</section>

<!-- Features Section -->
<section class="section-py section-gothic-secondary">
  <div class="container-custom">
    <div class="text-center mb-20">
      <h2 class="text-3xl md:text-4xl font-elegant font-bold text-gothic-white mb-6 gothic-ornament">
        Why Choose Us
      </h2>
      <p class="text-xl text-gothic-secondary max-w-2xl mx-auto">
        We make ordering from China as simple and secure as possible
      </p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
      <!-- Feature 1 -->
      {#if mounted}
        <div in:fly={{ y: 30, duration: 600, delay: 100 }}>
          <div class="card-gothic p-8 text-center hover-lift hover-glow">
            <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
              <div class="w-8 h-8 bg-gothic-accent rounded-full"></div>
            </div>
            <h3 class="text-xl font-elegant font-bold text-gothic-white mb-4">Reliability</h3>
            <p class="text-gothic-secondary leading-relaxed">
              We work with verified suppliers. We guarantee order delivery or full refund.
            </p>
          </div>
        </div>
      {:else}
        <div class="card-gothic p-8 text-center hover-lift hover-glow">
          <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
            <div class="w-8 h-8 bg-gothic-accent rounded-full"></div>
          </div>
          <h3 class="text-xl font-elegant font-bold text-gothic-white mb-4">Reliability</h3>
          <p class="text-gothic-secondary leading-relaxed">
            We work with verified suppliers. We guarantee order delivery or full refund.
          </p>
        </div>
      {/if}

      <!-- Feature 2 -->
      {#if mounted}
        <div in:fly={{ y: 30, duration: 600, delay: 200 }}>
          <div class="card-gothic p-8 text-center hover-lift hover-glow">
            <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
              <div class="w-8 h-8 border-2 border-gothic-accent rounded-full"></div>
            </div>
            <h3 class="text-xl font-elegant font-bold text-gothic-white mb-4">Competitive Prices</h3>
            <p class="text-gothic-secondary leading-relaxed">
              Fair 10% commission, current exchange rates, no hidden fees.
            </p>
          </div>
        </div>
      {:else}
        <div class="card-gothic p-8 text-center hover-lift hover-glow">
          <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
            <div class="w-8 h-8 border-2 border-gothic-accent rounded-full"></div>
          </div>
          <h3 class="text-xl font-elegant font-bold text-gothic-white mb-4">Competitive Prices</h3>
          <p class="text-gothic-secondary leading-relaxed">
            Fair 10% commission, current exchange rates, no hidden fees.
          </p>
        </div>
      {/if}

      <!-- Feature 3 -->
      {#if mounted}
        <div in:fly={{ y: 30, duration: 600, delay: 300 }}>
          <div class="card-gothic p-8 text-center hover-lift hover-glow">
            <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
              <div class="w-8 h-8 bg-gradient-to-br from-gothic-accent to-gothic-charcoal rounded-full"></div>
            </div>
            <h3 class="text-xl font-elegant font-bold text-gothic-white mb-4">Fast Delivery</h3>
            <p class="text-gothic-secondary leading-relaxed">
              Delivery from 2 weeks. Tracking at every stage from order to receipt.
            </p>
          </div>
        </div>
      {:else}
        <div class="card-gothic p-8 text-center hover-lift hover-glow">
          <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
            <div class="w-8 h-8 bg-gradient-to-br from-gothic-accent to-gothic-charcoal rounded-full"></div>
          </div>
          <h3 class="text-xl font-elegant font-bold text-gothic-white mb-4">Fast Delivery</h3>
          <p class="text-gothic-secondary leading-relaxed">
            Delivery from 2 weeks. Tracking at every stage from order to receipt.
          </p>
        </div>
      {/if}
    </div>
  </div>
</section>

<!-- How it works -->
<section class="section-py section-gothic-primary">
  <div class="container-custom">
    <div class="text-center mb-20">
      <h2 class="text-3xl md:text-4xl font-elegant font-bold text-gothic-white mb-6 gothic-ornament">
        How It Works
      </h2>
      <p class="text-xl text-gothic-secondary max-w-2xl mx-auto">
        Simple 4-step process
      </p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-8">
      <!-- Step 1 -->
      <div class="text-center group">
        <div class="w-16 h-16 glass-intense rounded-full flex items-center justify-center mx-auto mb-6 font-bold text-xl text-gothic-white group-hover:scale-110 transition-transform duration-300">
          1
        </div>
        <h3 class="text-lg font-elegant font-semibold text-gothic-white mb-3">Create Order</h3>
        <p class="text-gothic-secondary text-sm leading-relaxed">
          Specify product links and contact information
        </p>
      </div>

      <!-- Step 2 -->
      <div class="text-center group">
        <div class="w-16 h-16 glass-intense rounded-full flex items-center justify-center mx-auto mb-6 font-bold text-xl text-gothic-white group-hover:scale-110 transition-transform duration-300">
          2
        </div>
        <h3 class="text-lg font-elegant font-semibold text-gothic-white mb-3">Get Quote</h3>
        <p class="text-gothic-secondary text-sm leading-relaxed">
          We calculate the cost including commission and delivery
        </p>
      </div>

      <!-- Step 3 -->
      <div class="text-center group">
        <div class="w-16 h-16 glass-intense rounded-full flex items-center justify-center mx-auto mb-6 font-bold text-xl text-gothic-white group-hover:scale-110 transition-transform duration-300">
          3
        </div>
        <h3 class="text-lg font-elegant font-semibold text-gothic-white mb-3">Make Payment</h3>
        <p class="text-gothic-secondary text-sm leading-relaxed">
          Pay for the order using your preferred method
        </p>
      </div>

      <!-- Step 4 -->
      <div class="text-center group">
        <div class="w-16 h-16 glass-intense rounded-full flex items-center justify-center mx-auto mb-6 font-bold text-xl text-gothic-white group-hover:scale-110 transition-transform duration-300">
          4
        </div>
        <h3 class="text-lg font-elegant font-semibold text-gothic-white mb-3">Receive Products</h3>
        <p class="text-gothic-secondary text-sm leading-relaxed">
          Track delivery and receive your package
        </p>
      </div>
    </div>
  </div>
</section>

<!-- CTA Section -->
<section class="section-py relative overflow-hidden section-gothic-secondary pattern-overlay-7">
  
  <div class="container-custom text-center relative z-10">
    <h2 class="text-3xl md:text-4xl font-elegant font-bold text-gothic-white mb-6 gothic-ornament">
      Ready to Place an Order?
    </h2>
    <p class="text-xl text-gothic-secondary mb-12 max-w-2xl mx-auto">
      Join thousands of satisfied customers
    </p>
    
    <div class="flex flex-col sm:flex-row gap-6 justify-center items-center">
      <a href="/create" class="btn-gothic hover-lift shadow-gothic-glow">
        Create Order Now
      </a>
      
      <a href="/stories" class="btn-white hover-lift">
        Customer Stories
      </a>
    </div>
  </div>
</section>