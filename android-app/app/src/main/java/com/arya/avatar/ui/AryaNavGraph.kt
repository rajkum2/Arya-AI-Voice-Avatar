package com.arya.avatar.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.arya.avatar.ui.screens.AvatarDetailScreen
import com.arya.avatar.ui.screens.ConsentScreen
import com.arya.avatar.ui.screens.ConversationScreen
import com.arya.avatar.ui.screens.GalleryScreen
import com.arya.avatar.ui.screens.LoginScreen
import com.arya.avatar.ui.screens.OnboardingScreen
import com.arya.avatar.ui.screens.SplashScreen
import com.arya.avatar.ui.screens.SummaryScreen

object Routes {
    const val SPLASH = "splash"
    const val ONBOARDING = "onboarding"
    const val LOGIN = "login"
    const val CONSENT = "consent"
    const val GALLERY = "gallery"
    const val AVATAR = "avatar/{id}"
    const val CONVERSATION = "conversation/{sessionId}"
    const val SUMMARY = "summary/{sessionId}"
    fun avatar(id: String) = "avatar/$id"
    fun conversation(id: String) = "conversation/$id"
    fun summary(id: String) = "summary/$id"
}

@Composable
fun AryaNavGraph(vm: AppViewModel = hiltViewModel()) {
    val nav = rememberNavController()
    var start by remember { mutableStateOf(Routes.SPLASH) }

    NavHost(navController = nav, startDestination = start) {
        composable(Routes.SPLASH) {
            SplashScreen(
                onDone = { dest ->
                    nav.navigate(dest) {
                        popUpTo(Routes.SPLASH) { inclusive = true }
                    }
                },
                viewModel = vm,
            )
        }
        composable(Routes.ONBOARDING) {
            OnboardingScreen(onDone = { nav.navigate(Routes.LOGIN) { popUpTo(0) } })
        }
        composable(Routes.LOGIN) {
            LoginScreen(
                viewModel = vm,
                onLoggedIn = { needsConsent ->
                    nav.navigate(if (needsConsent) Routes.CONSENT else Routes.GALLERY) {
                        popUpTo(0)
                    }
                },
            )
        }
        composable(Routes.CONSENT) {
            ConsentScreen(
                viewModel = vm,
                onDone = { nav.navigate(Routes.GALLERY) { popUpTo(0) } },
            )
        }
        composable(Routes.GALLERY) {
            GalleryScreen(
                viewModel = vm,
                onAvatar = { id -> nav.navigate(Routes.avatar(id)) },
            )
        }
        composable(
            Routes.AVATAR,
            arguments = listOf(navArgument("id") { type = NavType.StringType }),
        ) { entry ->
            val id = entry.arguments?.getString("id") ?: return@composable
            AvatarDetailScreen(
                avatarId = id,
                viewModel = vm,
                onStart = { sessionId -> nav.navigate(Routes.conversation(sessionId)) },
                onBack = { nav.popBackStack() },
            )
        }
        composable(
            Routes.CONVERSATION,
            arguments = listOf(navArgument("sessionId") { type = NavType.StringType }),
        ) { entry ->
            val sessionId = entry.arguments?.getString("sessionId") ?: return@composable
            ConversationScreen(
                sessionId = sessionId,
                viewModel = vm,
                onEnd = { nav.navigate(Routes.summary(sessionId)) { popUpTo(Routes.GALLERY) } },
            )
        }
        composable(
            Routes.SUMMARY,
            arguments = listOf(navArgument("sessionId") { type = NavType.StringType }),
        ) {
            SummaryScreen(onGallery = {
                nav.navigate(Routes.GALLERY) { popUpTo(0) }
            })
        }
    }
}
