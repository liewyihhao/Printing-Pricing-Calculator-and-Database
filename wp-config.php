<?php



/**
 * The base configuration for WordPress
 *
 * The wp-config.php creation script uses this file during the
 * installation. You don't have to use the web site, you can
 * copy this file to "wp-config.php" and fill in the values.
 *
 * This file contains the following configurations:
 *
 * * MySQL settings
 * * Secret keys
 * * Database table prefix
 * * ABSPATH
 *
 * @link https://codex.wordpress.org/Editing_wp-config.php
 *
 * @package WordPress
 */
// ** MySQL settings - You can get this info from your web host ** //
/** The name of the database for WordPress */
define( 'DB_NAME', 'prin_printoka' );
/** MySQL database username */
define( 'DB_USER', 'prin_admin' );
/** MySQL database password */
define( 'DB_PASSWORD', 'Lnn$n961' );
/** MySQL hostname */
define( 'DB_HOST', 'localhost' );
/** Database Charset to use in creating database tables. */
define( 'DB_CHARSET', 'utf8mb4' );
/** The Database Collate type. Don't change this if in doubt. */
define( 'DB_COLLATE', '' );
// wp smtp
define( 'WPMS_ON', true );
define( 'WPMS_SMTP_PASS', 'gNs7?h91' );
// increase memory limit
define( 'WP_MEMORY_LIMIT', '516M' );
/**#@+
 * Authentication Unique Keys and Salts.
 *
 * Change these to different unique phrases!
 * You can generate these using the {@link https://api.wordpress.org/secret-key/1.1/salt/ WordPress.org secret-key service}
 * You can change these at any point in time to invalidate all existing cookies. This will force all users to have to log in again.
 *
 * @since 2.6.0
 */
define( 'AUTH_KEY', 'xqO|d<nO XXj{+l~MjR0Rcx4|h7G}fWq6[2`ZZNjO(^Z)Q(ob6*<VOS1O)-zZ.oI' );
define( 'SECURE_AUTH_KEY', 'V)n`$O-,e(7UI/Ks>&Q/`]X>UvTz4s,`Pato4PiY$2gj=])$X#wuBqL*xR~n-:,y' );
define( 'LOGGED_IN_KEY', 'w=2*#D={Xn3`E>#[8o8u;dG:xIJ])bgoPpWyg,wOmX@K3eEyJ.2lS1wZ3JQf>a/h' );
define( 'NONCE_KEY', '{9$g{s<l|zy8^W@m?H{t*ubD2@9-&|bn2kb!)<,Dd:%`Nf>oQ-cM-[pm~rnqa U.' );
define( 'AUTH_SALT', 'P/skK?R58u.YkKB(F=QFr^2zp~TceGxuz&cTlz.40Z)$;1?s4[$}t}sT,6)Yobn8' );
define( 'SECURE_AUTH_SALT', 'rSkuYJ!jk{|y`j%eH<W_3O&FE5W47$eSP2LKJ;Hkqv6{3&0QFpvFZZQ3z!zj0K-v' );
define( 'LOGGED_IN_SALT', '<PF>tZVsABL4>e/8xaCH8_*=zcKPK1YM^m&Of6tBO/{tu+;aXZ0q*$P>;i8Q7;M8' );
define( 'NONCE_SALT', ',ic+>KBa@3Y(AEDou34]cW]wR+Nz16a8+`/Bb/+n=M] kqh:~+F$5i?zGCRjz8Qj' );
/**#@-*/
/**
 * WordPress Database Table prefix.
 *
 * You can have multiple installations in one database if you give each
 * a unique prefix. Only numbers, letters, and underscores please!
 */
$table_prefix = 'printoka_';
/**
 * For developers: WordPress debugging mode.
 *
 * Change this to true to enable the display of notices during development.
 * It is strongly recommended that plugin and theme developers use WP_DEBUG
 * in their development environments.
 *
 * For information on other constants that can be used for debugging,
 * visit the Codex.
 *
 * @link https://codex.wordpress.org/Debugging_in_WordPress
 */
define( 'WP_DEBUG', true );
define( 'WP_DEBUG_LOG', true );
define( 'WP_DEBUG_DISPLAY', false );

// Set PHP error reporting level
error_reporting( E_ALL & ~E_DEPRECATED & ~E_USER_DEPRECATED & ~E_NOTICE );

// Ensure PHP doesn't display errors
@ini_set( 'display_errors', 0 );
@ini_set( 'log_errors', 1 );

define( 'DISABLE_WP_CRON', 'true' );
/* That's all, stop editing! Happy blogging. */
/** Absolute path to the WordPress directory. */
if ( ! defined( 'ABSPATH' ) ) {
	define( 'ABSPATH', dirname( __FILE__ ) . '/' );
}
// change default upload folder
define( 'UPLOADS', 'media' );
// disable upload fitlers
define( 'ALLOW_UNFILTERED_UPLOADS', true );
/** Sets up WordPress vars and included files. */
require_once ABSPATH . 'wp-settings.php';
