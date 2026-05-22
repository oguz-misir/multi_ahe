// Republishes nav_msgs/Odometry pose as a TF transform at 10 Hz.
//
// Gazebo stops publishing TF for stationary robots, causing the TF cache
// to expire after 10 s.  The Odometry message is always published even when
// stationary, so this node keeps the odom→base_link TF alive.
//
// Design: subscription callback only stores the latest message pointer
// (no copy, no publish).  A wall-timer fires at 10 Hz and does the actual
// TF broadcast.  This keeps CPU usage well below 1%.
//
// Deployed per robot in its namespace so the relative "odom" topic
// resolves to /robot_N/odom.

#include <memory>
#include <rclcpp/rclcpp.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>
#include <tf2_ros/transform_broadcaster.h>

class OdomToTF : public rclcpp::Node
{
public:
  OdomToTF()
  : Node("odom_to_tf")
  {
    broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);

    sub_ = create_subscription<nav_msgs::msg::Odometry>(
      "odom", rclcpp::QoS(10),
      [this](nav_msgs::msg::Odometry::SharedPtr msg) { latest_ = std::move(msg); });

    timer_ = rclcpp::create_timer(
      this,
      this->get_clock(),               // sim-time aware clock
      rclcpp::Duration::from_seconds(0.1),
      [this]() { publish(); });
  }

private:
  void publish()
  {
    if (!latest_) return;

    geometry_msgs::msg::TransformStamped t;
    t.header.stamp    = this->now();
    t.header.frame_id = latest_->header.frame_id;
    t.child_frame_id  = latest_->child_frame_id;
    t.transform.translation.x = latest_->pose.pose.position.x;
    t.transform.translation.y = latest_->pose.pose.position.y;
    t.transform.translation.z = latest_->pose.pose.position.z;
    t.transform.rotation      = latest_->pose.pose.orientation;

    broadcaster_->sendTransform(t);
  }

  std::unique_ptr<tf2_ros::TransformBroadcaster> broadcaster_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr sub_;
  rclcpp::TimerBase::SharedPtr timer_;
  nav_msgs::msg::Odometry::SharedPtr latest_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<OdomToTF>());
  rclcpp::shutdown();
  return 0;
}
