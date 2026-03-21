<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Courier New', monospace;
  background: #0a0a0f;
  color: #fff;
  min-height: 100vh;
}

a {
  color: inherit;
  text-decoration: none;
}

#app {
  min-height: 100vh;
}
</style>
