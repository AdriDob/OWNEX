import 'react-native-gesture-handler';
import * as React from 'react';
import { registerRootComponent } from 'expo';
import { Providers } from './src/providers';
import { AppNavigator } from './src/navigation/AppNavigator';

export default function App() {
  return (
    <Providers>
      <AppNavigator />
    </Providers>
  );
}

registerRootComponent(App);